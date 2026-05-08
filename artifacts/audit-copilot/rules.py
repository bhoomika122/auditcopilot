import pandas as pd
import numpy as np
from scipy import stats
from rapidfuzz import fuzz
from itertools import combinations

APPROVAL_THRESHOLD = 10000.0
ROUND_DOLLAR_THRESHOLD = 50000.0
SPLIT_PO_WINDOW_DAYS = 30
SPLIT_PO_WINDOW_PCT = 0.10
FUZZY_MATCH_THRESHOLD = 85


def detect_duplicate_vendors(df: pd.DataFrame) -> pd.DataFrame:
    vendor_names = df["vendor_name"].unique().tolist()
    flagged_pairs: dict[str, list[str]] = {}
    for a, b in combinations(vendor_names, 2):
        score = fuzz.ratio(a.lower(), b.lower())
        if score >= FUZZY_MATCH_THRESHOLD and a != b:
            flagged_pairs.setdefault(a, []).append(b)
            flagged_pairs.setdefault(b, []).append(a)

    results = []
    for idx, row in df.iterrows():
        if row["vendor_name"] in flagged_pairs:
            matches = flagged_pairs[row["vendor_name"]]
            results.append({
                "transaction_id": row["transaction_id"],
                "flag_category": "Duplicate Vendor",
                "risk_level": "High",
                "rule_explanation": (
                    f"Vendor '{row['vendor_name']}' is suspiciously similar to: "
                    f"{', '.join(matches)}. Possible ghost vendor or duplicate payee "
                    f"(fuzzy match score >= {FUZZY_MATCH_THRESHOLD}%)."
                ),
            })
    return pd.DataFrame(results)


def benford_test(df: pd.DataFrame) -> pd.DataFrame:
    amounts = df["amount"].dropna()
    amounts = amounts[amounts > 0]

    def first_digit(x):
        s = str(abs(x)).replace(".", "").lstrip("0")
        return int(s[0]) if s else None

    digits = amounts.apply(first_digit).dropna().astype(int)
    digits = digits[digits.between(1, 9)]

    observed_counts = np.array([
        (digits == d).sum() for d in range(1, 10)
    ])
    n = observed_counts.sum()
    expected_probs = np.array([np.log10(1 + 1 / d) for d in range(1, 10)])
    expected_counts = expected_probs * n

    chi2, p_value = stats.chisquare(observed_counts, expected_counts)

    results = []
    if p_value < 0.05:
        observed_freq = observed_counts / n
        for d in range(1, 10):
            deviation = abs(observed_freq[d - 1] - expected_probs[d - 1])
            if deviation > 0.04:
                flagged_txns = df[df["amount"].apply(first_digit) == d]
                for idx, row in flagged_txns.iterrows():
                    results.append({
                        "transaction_id": row["transaction_id"],
                        "flag_category": "Benford's Law Violation",
                        "risk_level": "Medium",
                        "rule_explanation": (
                            f"Invoice amount ${row['amount']:,.2f} starts with digit '{d}'. "
                            f"Benford's Law chi-square test yields p={p_value:.4f} (< 0.05), "
                            f"suggesting potential manipulation. Digit '{d}' observed at "
                            f"{observed_freq[d-1]*100:.1f}% vs expected {expected_probs[d-1]*100:.1f}%."
                        ),
                    })
    return pd.DataFrame(results)


def detect_round_dollar(df: pd.DataFrame, threshold: float = ROUND_DOLLAR_THRESHOLD) -> pd.DataFrame:
    mask = (df["amount"] % 1 == 0) & (df["amount"] >= threshold)
    flagged = df[mask].copy()
    results = []
    for idx, row in flagged.iterrows():
        results.append({
            "transaction_id": row["transaction_id"],
            "flag_category": "Round-Dollar Payment",
            "risk_level": "Medium",
            "rule_explanation": (
                f"Invoice amount ${row['amount']:,.2f} is a round-dollar figure "
                f"above the ${threshold:,.0f} threshold. Round amounts above materiality "
                f"thresholds are a common indicator of fictitious invoices or estimates "
                f"billed as actuals."
            ),
        })
    return pd.DataFrame(results)


def detect_weekend_postings(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_posting_dt"] = pd.to_datetime(df["posting_date"], errors="coerce")
    mask = df["_posting_dt"].dt.dayofweek >= 5
    flagged = df[mask].copy()
    results = []
    for idx, row in flagged.iterrows():
        day_name = row["_posting_dt"].strftime("%A")
        results.append({
            "transaction_id": row["transaction_id"],
            "flag_category": "Weekend Posting",
            "risk_level": "Medium",
            "rule_explanation": (
                f"Transaction posted on {day_name} {row['posting_date']}. "
                f"Weekend postings bypass standard approval workflows and may "
                f"indicate unauthorized or fraudulent transactions."
            ),
        })
    return pd.DataFrame(results)


def detect_split_po(
    df: pd.DataFrame,
    approval_threshold: float = APPROVAL_THRESHOLD,
    window_pct: float = SPLIT_PO_WINDOW_PCT,
    window_days: int = SPLIT_PO_WINDOW_DAYS,
) -> pd.DataFrame:
    df = df.copy()
    df["_inv_dt"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    lower_bound = approval_threshold * (1 - window_pct)
    suspect = df[(df["amount"] >= lower_bound) & (df["amount"] < approval_threshold)].copy()
    suspect = suspect.sort_values("_inv_dt")

    results = []
    seen = set()
    for vendor_id in suspect["vendor_id"].unique():
        vendor_rows = suspect[suspect["vendor_id"] == vendor_id].reset_index(drop=True)
        if len(vendor_rows) < 2:
            continue
        for i in range(len(vendor_rows)):
            for j in range(i + 1, len(vendor_rows)):
                dt_i = vendor_rows.loc[i, "_inv_dt"]
                dt_j = vendor_rows.loc[j, "_inv_dt"]
                if pd.isna(dt_i) or pd.isna(dt_j):
                    continue
                if abs((dt_j - dt_i).days) <= window_days:
                    for k in [i, j]:
                        tid = vendor_rows.loc[k, "transaction_id"]
                        if tid not in seen:
                            seen.add(tid)
                            row = vendor_rows.loc[k]
                            results.append({
                                "transaction_id": tid,
                                "flag_category": "Split-PO Pattern",
                                "risk_level": "High",
                                "rule_explanation": (
                                    f"Vendor '{row['vendor_name']}' has multiple invoices "
                                    f"(${row['amount']:,.2f}) within {window_pct*100:.0f}% below "
                                    f"the ${approval_threshold:,.0f} approval threshold, "
                                    f"posted within {window_days} days. Classic threshold-splitting "
                                    f"to circumvent authorization controls."
                                ),
                            })
    return pd.DataFrame(results)


def detect_fx_mismatch(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["currency"] != df["gl_account_currency"]
    flagged = df[mask].copy()
    results = []
    for idx, row in flagged.iterrows():
        results.append({
            "transaction_id": row["transaction_id"],
            "flag_category": "FX Misallocation",
            "risk_level": "High",
            "rule_explanation": (
                f"Invoice currency is {row['currency']} but GL account "
                f"'{row['gl_account']}' is designated for {row['gl_account_currency']}. "
                f"This mismatch may cause unrealized FX gains/losses and misstate "
                f"financials under IAS 21."
            ),
        })
    return pd.DataFrame(results)


def detect_duplicate_invoice_numbers(df: pd.DataFrame) -> pd.DataFrame:
    dup_inv = df.groupby("invoice_number").filter(
        lambda x: x["vendor_id"].nunique() > 1
    )
    results = []
    for idx, row in dup_inv.iterrows():
        other_vendors = df[
            (df["invoice_number"] == row["invoice_number"]) &
            (df["vendor_id"] != row["vendor_id"])
        ]["vendor_name"].tolist()
        results.append({
            "transaction_id": row["transaction_id"],
            "flag_category": "Duplicate Invoice Number",
            "risk_level": "High",
            "rule_explanation": (
                f"Invoice number '{row['invoice_number']}' from vendor "
                f"'{row['vendor_name']}' appears across multiple vendors: "
                f"{', '.join(other_vendors)}. Possible duplicate payment or "
                f"invoice fraud."
            ),
        })
    return pd.DataFrame(results)


def run_all_rules(df: pd.DataFrame) -> pd.DataFrame:
    rule_results = []

    checks = [
        ("Duplicate Vendor", detect_duplicate_vendors),
        ("Benford's Law", benford_test),
        ("Round-Dollar", detect_round_dollar),
        ("Weekend Posting", detect_weekend_postings),
        ("Split-PO", detect_split_po),
        ("FX Mismatch", detect_fx_mismatch),
        ("Duplicate Invoice #", detect_duplicate_invoice_numbers),
    ]

    for name, fn in checks:
        try:
            result = fn(df)
            if not result.empty:
                rule_results.append(result)
        except Exception:
            pass

    if not rule_results:
        return pd.DataFrame(columns=[
            "transaction_id", "flag_category", "risk_level", "rule_explanation"
        ])

    flags = pd.concat(rule_results, ignore_index=True)
    flags = flags.drop_duplicates(subset=["transaction_id", "flag_category"])
    merged = df.merge(flags, on="transaction_id", how="inner")
    return merged
