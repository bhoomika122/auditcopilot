import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

REAL_VENDORS = [
    ("McKesson Corporation", "V001", "USD"),
    ("Cardinal Health Inc", "V002", "USD"),
    ("AmerisourceBergen Corp", "V003", "USD"),
    ("Henry Schein Inc", "V004", "USD"),
    ("Medline Industries LP", "V005", "USD"),
    ("Becton Dickinson & Co", "V006", "USD"),
    ("Stryker Corporation", "V007", "USD"),
    ("Johnson & Johnson Medical", "V008", "USD"),
    ("Baxter International Inc", "V009", "USD"),
    ("Abbott Laboratories", "V010", "USD"),
    ("Thermo Fisher Scientific", "V011", "USD"),
    ("Owens & Minor Inc", "V012", "USD"),
    ("Medtronic PLC", "V013", "USD"),
    ("Boston Scientific Corp", "V014", "USD"),
    ("Zimmer Biomet Holdings", "V015", "USD"),
    ("ICU Medical Inc", "V016", "USD"),
    ("Haemonetics Corporation", "V017", "USD"),
    ("Integra LifeSciences", "V018", "USD"),
    ("NovaBay Pharmaceuticals", "V019", "USD"),
    ("Natus Medical Inc", "V020", "USD"),
]

SMALL_VENDORS = [
    ("HealthTech Supplies LLC", "V021", "USD"),
    ("Prestige Medical Corp", "V022", "USD"),
    ("ClinEdge Inc", "V023", "USD"),
    ("MedCore Solutions", "V024", "USD"),
    ("Pacific Medical Group", "V025", "USD"),
    ("Summit Health Products", "V026", "USD"),
    ("Alpine Medical Supply", "V027", "USD"),
    ("Riverside Healthcare Svcs", "V028", "USD"),
    ("BlueRidge Pharma LLC", "V029", "USD"),
    ("Horizon Medical Devices", "V030", "USD"),
    ("Crestview Lab Services", "V031", "USD"),
    ("Pinnacle Diagnostics Inc", "V032", "USD"),
    ("Clearwater Biomedical", "V033", "USD"),
    ("TrueNorth Health Svcs", "V034", "USD"),
    ("Keystone Med Supply", "V035", "USD"),
]

GL_ACCOUNTS = {
    "USD": ["6100-USD", "6200-USD", "6300-USD", "6400-USD"],
    "EUR": ["6100-EUR", "6200-EUR"],
    "GBP": ["6100-GBP"],
}

APPROVERS = [
    "J.Martinez", "S.Williams", "T.Johnson", "R.Patel",
    "L.Chen", "M.Davis", "K.Thompson", "A.Gonzalez",
]

PAYMENT_METHODS = ["ACH", "Wire", "Check", "Credit Card"]


def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def random_business_date(start, end):
    d = random_date(start, end)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def generate_sample_data():
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    rows = []
    txn_counter = 1000

    def new_id():
        nonlocal txn_counter
        txn_counter += 1
        return f"TXN-{txn_counter}"

    def new_inv(prefix="INV"):
        return f"{prefix}-{random.randint(100000, 999999)}"

    # --- Normal transactions (roughly 170 clean rows) ---
    all_vendors = REAL_VENDORS + SMALL_VENDORS
    for _ in range(168):
        vendor = random.choice(all_vendors)
        vname, vid, vcurr = vendor
        inv_date = random_business_date(start_date, end_date)
        post_date = inv_date + timedelta(days=random.randint(1, 7))
        while post_date.weekday() >= 5:
            post_date += timedelta(days=1)
        amount = round(random.uniform(500, 49000), 2)
        gl_acct = random.choice(GL_ACCOUNTS[vcurr])
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": vname,
            "vendor_id": vid,
            "invoice_number": new_inv(),
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_date.strftime("%Y-%m-%d"),
            "amount": amount,
            "currency": vcurr,
            "gl_account": gl_acct,
            "gl_account_currency": vcurr,
            "approver": random.choice(APPROVERS),
            "payment_method": random.choice(PAYMENT_METHODS),
        })

    # ==========================================================
    # PLANTED ANOMALY 1: Duplicate Vendor Names (3 pairs)
    # ==========================================================
    dup_vendor_pairs = [
        # Pair A
        ("MedSupply Inc", "V099", "Med Supply Inc.", "V099B"),
        # Pair B
        ("ABC Pharma LLC", "V098", "ABC Pharma L.L.C.", "V098B"),
        # Pair C
        ("Global Med Corp", "V097", "Global Med Corp.", "V097B"),
    ]
    for name_a, vid_a, name_b, vid_b in dup_vendor_pairs:
        for vname, vid in [(name_a, vid_a), (name_b, vid_b)]:
            inv_date = random_business_date(start_date, end_date)
            post_date = inv_date + timedelta(days=random.randint(1, 5))
            while post_date.weekday() >= 5:
                post_date += timedelta(days=1)
            rows.append({
                "transaction_id": new_id(),
                "vendor_name": vname,
                "vendor_id": vid,
                "invoice_number": new_inv("DUPV"),
                "invoice_date": inv_date.strftime("%Y-%m-%d"),
                "posting_date": post_date.strftime("%Y-%m-%d"),
                "amount": round(random.uniform(10000, 80000), 2),
                "currency": "USD",
                "gl_account": "6200-USD",
                "gl_account_currency": "USD",
                "approver": random.choice(APPROVERS),
                "payment_method": "ACH",
            })

    # ==========================================================
    # PLANTED ANOMALY 2: Round-Dollar Payments (5 rows > $50K)
    # ==========================================================
    round_dollar_vendors = [
        ("McKesson Corporation", "V001"),
        ("Cardinal Health Inc", "V002"),
        ("Stryker Corporation", "V007"),
        ("Baxter International Inc", "V009"),
        ("Medtronic PLC", "V013"),
    ]
    round_amounts = [75000.00, 125000.00, 200000.00, 55000.00, 98000.00]
    for (vname, vid), amt in zip(round_dollar_vendors, round_amounts):
        inv_date = random_business_date(start_date, end_date)
        post_date = inv_date + timedelta(days=random.randint(1, 5))
        while post_date.weekday() >= 5:
            post_date += timedelta(days=1)
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": vname,
            "vendor_id": vid,
            "invoice_number": new_inv("RND"),
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_date.strftime("%Y-%m-%d"),
            "amount": amt,
            "currency": "USD",
            "gl_account": "6100-USD",
            "gl_account_currency": "USD",
            "approver": random.choice(APPROVERS),
            "payment_method": "Wire",
        })

    # ==========================================================
    # PLANTED ANOMALY 3: Weekend Postings (4 rows)
    # ==========================================================
    weekend_dates = [
        datetime(2024, 3, 2),   # Saturday
        datetime(2024, 5, 4),   # Saturday
        datetime(2024, 7, 7),   # Sunday
        datetime(2024, 9, 1),   # Sunday
    ]
    weekend_vendors = [
        ("HealthTech Supplies LLC", "V021"),
        ("Prestige Medical Corp", "V022"),
        ("ClinEdge Inc", "V023"),
        ("Summit Health Products", "V026"),
    ]
    for post_dt, (vname, vid) in zip(weekend_dates, weekend_vendors):
        inv_date = post_dt - timedelta(days=random.randint(1, 4))
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": vname,
            "vendor_id": vid,
            "invoice_number": new_inv("WKD"),
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_dt.strftime("%Y-%m-%d"),
            "amount": round(random.uniform(2000, 30000), 2),
            "currency": "USD",
            "gl_account": "6300-USD",
            "gl_account_currency": "USD",
            "approver": random.choice(APPROVERS),
            "payment_method": "Check",
        })

    # ==========================================================
    # PLANTED ANOMALY 4: Split-PO Patterns (3 vendors x 2 invoices)
    # ==========================================================
    split_po_vendors = [
        ("Pacific Medical Group", "V025"),
        ("Alpine Medical Supply", "V027"),
        ("BlueRidge Pharma LLC", "V029"),
    ]
    split_amounts = [
        (9500.00, 9800.00),
        (9750.00, 9900.00),
        (9450.00, 9850.00),
    ]
    for (vname, vid), (amt1, amt2) in zip(split_po_vendors, split_amounts):
        base_date = random_business_date(start_date, datetime(2024, 10, 1))
        for amt, offset_days in [(amt1, 0), (amt2, 12)]:
            inv_date = base_date + timedelta(days=offset_days)
            post_date = inv_date + timedelta(days=2)
            rows.append({
                "transaction_id": new_id(),
                "vendor_name": vname,
                "vendor_id": vid,
                "invoice_number": new_inv("SPO"),
                "invoice_date": inv_date.strftime("%Y-%m-%d"),
                "posting_date": post_date.strftime("%Y-%m-%d"),
                "amount": amt,
                "currency": "USD",
                "gl_account": "6200-USD",
                "gl_account_currency": "USD",
                "approver": random.choice(APPROVERS),
                "payment_method": "ACH",
            })

    # ==========================================================
    # PLANTED ANOMALY 5: FX Mismatches (4 rows - USD invoice to EUR GL)
    # ==========================================================
    fx_mismatch_vendors = [
        ("Becton Dickinson & Co", "V006"),
        ("Thermo Fisher Scientific", "V011"),
        ("NovaBay Pharmaceuticals", "V019"),
        ("Clearwater Biomedical", "V033"),
    ]
    for vname, vid in fx_mismatch_vendors:
        inv_date = random_business_date(start_date, end_date)
        post_date = inv_date + timedelta(days=3)
        while post_date.weekday() >= 5:
            post_date += timedelta(days=1)
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": vname,
            "vendor_id": vid,
            "invoice_number": new_inv("FX"),
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_date.strftime("%Y-%m-%d"),
            "amount": round(random.uniform(5000, 40000), 2),
            "currency": "USD",
            "gl_account": "6100-EUR",
            "gl_account_currency": "EUR",
            "approver": random.choice(APPROVERS),
            "payment_method": "Wire",
        })

    # ==========================================================
    # PLANTED ANOMALY 6: Duplicate Invoice Numbers (2 pairs across vendors)
    # ==========================================================
    dup_inv_number = "INV-DUP-77421"
    for vname, vid in [("Johnson & Johnson Medical", "V008"), ("ICU Medical Inc", "V016")]:
        inv_date = random_business_date(start_date, end_date)
        post_date = inv_date + timedelta(days=2)
        while post_date.weekday() >= 5:
            post_date += timedelta(days=1)
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": vname,
            "vendor_id": vid,
            "invoice_number": dup_inv_number,
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_date.strftime("%Y-%m-%d"),
            "amount": round(random.uniform(8000, 25000), 2),
            "currency": "USD",
            "gl_account": "6400-USD",
            "gl_account_currency": "USD",
            "approver": random.choice(APPROVERS),
            "payment_method": "ACH",
        })

    dup_inv_number_2 = "INV-DUP-33908"
    for vname, vid in [("Medline Industries LP", "V005"), ("Riverside Healthcare Svcs", "V028")]:
        inv_date = random_business_date(start_date, end_date)
        post_date = inv_date + timedelta(days=3)
        while post_date.weekday() >= 5:
            post_date += timedelta(days=1)
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": vname,
            "vendor_id": vid,
            "invoice_number": dup_inv_number_2,
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_date.strftime("%Y-%m-%d"),
            "amount": round(random.uniform(12000, 35000), 2),
            "currency": "USD",
            "gl_account": "6300-USD",
            "gl_account_currency": "USD",
            "approver": random.choice(APPROVERS),
            "payment_method": "Check",
        })

    # ==========================================================
    # PLANTED ANOMALY 7: Ghost Vendor - no real address, round-dollar amounts
    # ==========================================================
    ghost_vendor_name = "Quantum Health Solutions LLC"
    ghost_vendor_id = "V999"
    for amt in [50000.00, 75000.00]:
        inv_date = random_business_date(start_date, end_date)
        post_date = inv_date + timedelta(days=2)
        while post_date.weekday() >= 5:
            post_date += timedelta(days=1)
        rows.append({
            "transaction_id": new_id(),
            "vendor_name": ghost_vendor_name,
            "vendor_id": ghost_vendor_id,
            "invoice_number": new_inv("GHO"),
            "invoice_date": inv_date.strftime("%Y-%m-%d"),
            "posting_date": post_date.strftime("%Y-%m-%d"),
            "amount": amt,
            "currency": "USD",
            "gl_account": "6200-USD",
            "gl_account_currency": "USD",
            "approver": "J.Martinez",
            "payment_method": "Wire",
        })

    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    return df
