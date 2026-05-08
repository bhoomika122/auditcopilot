import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import json
import os

from data_generator import generate_sample_data
from rules import run_all_rules, benford_test
from ai_memo import generate_memo
from excel_export import build_workpaper

st.set_page_config(
    page_title="AuditCopilot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (minimal, professional) ──────────────────────────────────────
st.markdown("""
<style>
  .main-header {
    background: linear-gradient(90deg, #0B2545 0%, #163a6b 100%);
    color: white;
    padding: 18px 24px;
    border-radius: 8px;
    margin-bottom: 20px;
  }
  .main-header h1 { color: white; margin: 0; font-size: 2rem; }
  .main-header p  { color: #C9A961; margin: 4px 0 0; font-size: 1rem; }

  .kpi-card {
    background: white;
    border: 1px solid #ddd;
    border-left: 4px solid #C9A961;
    border-radius: 8px;
    padding: 16px 20px;
    text-align: center;
  }
  .kpi-label { font-size: 0.8rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }
  .kpi-value { font-size: 1.8rem; font-weight: 700; color: #0B2545; line-height: 1.2; }
  .kpi-sub   { font-size: 0.75rem; color: #9ca3af; margin-top: 2px; }

  .story-banner {
    background: #0B2545;
    color: white;
    border-left: 5px solid #C9A961;
    border-radius: 6px;
    padding: 16px 20px;
    margin: 16px 0;
  }
  .story-banner h3 { color: #C9A961; margin: 0 0 6px; }
  .story-banner p  { margin: 0; line-height: 1.5; }

  .risk-high   { background:#fde8e8; color:#7f1d1d; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
  .risk-medium { background:#fef3c7; color:#78350f; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
  .risk-low    { background:#d1fae5; color:#064e3b; padding:3px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }

  div[data-testid="metric-container"] { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }

  footer { text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ──────────────────────────────────────────────────
if "df_raw" not in st.session_state:
    st.session_state.df_raw = None
if "df_flagged" not in st.session_state:
    st.session_state.df_flagged = None
if "ai_memos" not in st.session_state:
    st.session_state.ai_memos = {}
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "audit_run" not in st.session_state:
    st.session_state.audit_run = False
if "benford_summary" not in st.session_state:
    st.session_state.benford_summary = None


# ── Helpers ─────────────────────────────────────────────────────────────────
def load_demo_data():
    df = generate_sample_data()
    st.session_state.df_raw = df
    with st.spinner("Running forensic rule engine…"):
        st.session_state.df_flagged = run_all_rules(df)
        st.session_state.benford_summary = benford_test(df)
    st.session_state.audit_run = True
    st.session_state.ai_memos = {}
    st.session_state.page = "Risk Dashboard"
    st.rerun()


def benford_expected_probs():
    return [np.log10(1 + 1 / d) for d in range(1, 10)]


def first_digit_dist(amounts):
    def fd(x):
        s = str(abs(x)).replace(".", "").lstrip("0")
        return int(s[0]) if s else None
    digits = pd.Series(amounts).apply(fd).dropna().astype(int)
    digits = digits[digits.between(1, 9)]
    n = len(digits)
    return [(digits == d).sum() / n for d in range(1, 10)], n


def risk_badge(level: str) -> str:
    cls = {"High": "risk-high", "Medium": "risk-medium", "Low": "risk-low"}.get(level, "risk-low")
    return f'<span class="{cls}">{level}</span>'


# ── Sidebar navigation ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 AuditCopilot")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Home", "Upload & Run", "Risk Dashboard", "Export Workpaper"],
        index=["Home", "Upload & Run", "Risk Dashboard", "Export Workpaper"].index(
            st.session_state.page
        ),
        label_visibility="collapsed",
    )
    st.session_state.page = page
    st.markdown("---")

    if st.session_state.audit_run and st.session_state.df_flagged is not None:
        df_f = st.session_state.df_flagged
        st.markdown("**Audit Status**")
        st.success(f"✓ {len(st.session_state.df_raw):,} transactions reviewed")
        st.warning(f"⚠ {len(df_f):,} flags detected")
    else:
        st.info("No audit data loaded. Go to Home or Upload & Run.")

    st.markdown("---")
    st.markdown(
        "<small>Built by Bhoomika Bothra<br>CA, ICAI</small>",
        unsafe_allow_html=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — HOME
# ════════════════════════════════════════════════════════════════════════════
if page == "Home":
    st.markdown("""
    <div class="main-header">
      <h1>🔍 AuditCopilot</h1>
      <p>AI-assisted forensic AP review for healthcare finance teams</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### What AuditCopilot does")
        st.markdown("""
        Healthcare AP teams spend **60–70% of review time** manually scanning for:
        - Ghost vendors and duplicate payees
        - Benford's Law violations in invoice amounts
        - Round-dollar payments above materiality thresholds
        - Weekend and holiday postings that bypass controls
        - Split-PO patterns designed to circumvent approval thresholds
        - FX misallocations across currency-designated GL accounts
        - Duplicate invoice numbers across vendors

        AuditCopilot automates the **detection layer** and the **documentation layer**
        so your team focuses on judgment — not scanning.
        """)

        st.markdown("""
        <div class="story-banner">
          <h3>📖 Inspired by a real finding</h3>
          <p>In 2023, a forensic audit team at a major pharma distributor uncovered a
          <strong>$1.2M ghost vendor scheme</strong> using fuzzy vendor-name matching and
          round-dollar payment analysis — exactly the rules built into AuditCopilot.
          The vendor had been active for 18 months across 4 GL accounts before detection.
          Automated detection would have flagged it in the first quarter.</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Forensic Rule Engine")
        rules = [
            ("🔍", "Duplicate Vendor Detection", "Fuzzy name matching (>85% similarity)"),
            ("📊", "Benford's Law Analysis", "Chi-square test on first-digit distribution"),
            ("💰", "Round-Dollar Payments", "Amounts ending in .00 above threshold"),
            ("📅", "Weekend Postings", "Transactions posted on Saturday or Sunday"),
            ("✂️", "Split-PO Patterns", "Multiple invoices just under approval threshold"),
            ("💱", "FX Misallocation", "Currency mismatch vs. GL account designation"),
            ("📄", "Duplicate Invoice #s", "Same invoice number across multiple vendors"),
        ]
        for icon, name, desc in rules:
            st.markdown(f"**{icon} {name}**  \n<small style='color:#6b7280'>{desc}</small>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Ready to start?")
    col_a, col_b, col_c = st.columns([2, 2, 4])
    with col_a:
        if st.button("🚀 Try Demo Data", type="primary", use_container_width=True):
            load_demo_data()
    with col_b:
        if st.button("📤 Upload My CSV", use_container_width=True):
            st.session_state.page = "Upload & Run"
            st.rerun()

    st.markdown("""
    <footer>AuditCopilot · Built for Healthcare Finance Professionals ·
    Standards referenced: AU-C 240, AU-C 315, IAS 21</footer>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — UPLOAD & RUN
# ════════════════════════════════════════════════════════════════════════════
elif page == "Upload & Run":
    st.markdown("""
    <div class="main-header">
      <h1>🔍 AuditCopilot</h1>
      <p>Upload & Run — Load your AP data and run the forensic rule engine</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### Upload AP Transaction Data")
        st.markdown("""
        Upload a CSV file with the following columns:
        `transaction_id`, `vendor_name`, `vendor_id`, `invoice_number`,
        `invoice_date`, `posting_date`, `amount`, `currency`,
        `gl_account`, `gl_account_currency`, `approver`, `payment_method`
        """)

        uploaded = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded:
            try:
                df_up = pd.read_csv(uploaded)
                required_cols = [
                    "transaction_id", "vendor_name", "vendor_id",
                    "invoice_number", "invoice_date", "posting_date",
                    "amount", "currency", "gl_account",
                    "gl_account_currency", "approver", "payment_method"
                ]
                missing = [c for c in required_cols if c not in df_up.columns]
                if missing:
                    st.error(f"Missing columns: {', '.join(missing)}")
                else:
                    st.success(f"✓ Loaded {len(df_up):,} rows from {uploaded.name}")
                    st.dataframe(df_up.head(5), use_container_width=True)
                    if st.button("▶ Run Audit on Uploaded Data", type="primary"):
                        st.session_state.df_raw = df_up
                        with st.spinner("Running forensic rule engine…"):
                            st.session_state.df_flagged = run_all_rules(df_up)
                            st.session_state.benford_summary = benford_test(df_up)
                        st.session_state.audit_run = True
                        st.session_state.ai_memos = {}
                        st.session_state.page = "Risk Dashboard"
                        st.toast("Audit complete! Switching to dashboard.")
                        st.rerun()
            except Exception as e:
                st.error(f"Error reading CSV: {e}")

        st.markdown("---")
        st.markdown("### Or use the built-in demo dataset")
        st.markdown(
            "200+ synthetic healthcare AP transactions with 7 categories of planted anomalies."
        )
        if st.button("🚀 Use Sample Data & Run Audit", type="secondary", use_container_width=True):
            load_demo_data()

    with col2:
        st.markdown("### Expected CSV Format")
        sample_cols = {
            "transaction_id": "TXN-1001",
            "vendor_name": "McKesson Corp",
            "vendor_id": "V001",
            "invoice_number": "INV-123456",
            "invoice_date": "2024-03-15",
            "posting_date": "2024-03-17",
            "amount": "24500.00",
            "currency": "USD",
            "gl_account": "6100-USD",
            "gl_account_currency": "USD",
            "approver": "J.Martinez",
            "payment_method": "ACH",
        }
        st.dataframe(pd.DataFrame([sample_cols]).T.rename(columns={0: "Example"}), use_container_width=True)

        st.markdown("### Supported Anomaly Types")
        for cat in [
            "Duplicate Vendor Names",
            "Benford's Law Violations",
            "Round-Dollar Payments",
            "Weekend Postings",
            "Split-PO Patterns",
            "FX Misallocations",
            "Duplicate Invoice Numbers",
        ]:
            st.markdown(f"• {cat}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — RISK DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
elif page == "Risk Dashboard":
    st.markdown("""
    <div class="main-header">
      <h1>🔍 AuditCopilot</h1>
      <p>Risk Dashboard — Forensic analysis results and flagged transactions</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.audit_run or st.session_state.df_raw is None:
        st.warning("No audit data loaded. Please go to **Home** or **Upload & Run** first.")
        if st.button("🚀 Load Demo Data Now"):
            load_demo_data()
        st.stop()

    df_all = st.session_state.df_raw
    df_flagged = st.session_state.df_flagged

    # ── KPI Cards ────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("Total Transactions", f"{len(df_all):,}")
    with k2:
        st.metric("Flagged Transactions", f"{len(df_flagged):,}")
    with k3:
        dollar_risk = df_flagged["amount"].sum() if not df_flagged.empty else 0
        st.metric("Dollar Value at Risk", f"${dollar_risk:,.0f}")
    with k4:
        high_risk = len(df_flagged[df_flagged["risk_level"] == "High"]) if not df_flagged.empty else 0
        st.metric("High-Risk Flags", f"{high_risk}")

    st.markdown("---")

    if df_flagged.empty:
        st.success("✅ No anomalies detected in this dataset.")
        st.stop()

    # ── Charts ────────────────────────────────────────────────────────────────
    ch1, ch2 = st.columns(2)

    with ch1:
        st.markdown("#### Flags by Category")
        cat_counts = (
            df_flagged.groupby(["flag_category", "risk_level"])
            .size()
            .reset_index(name="count")
        )
        color_map = {"High": "#C73E3A", "Medium": "#E8A33D", "Low": "#3C8D5C"}
        fig_bar = px.bar(
            cat_counts,
            x="flag_category",
            y="count",
            color="risk_level",
            color_discrete_map=color_map,
            template="plotly_white",
            labels={"flag_category": "Flag Category", "count": "# Flags", "risk_level": "Risk"},
        )
        fig_bar.update_layout(
            xaxis_tickangle=-35,
            legend_title_text="Risk Level",
            plot_bgcolor="#F7F6F2",
            paper_bgcolor="#F7F6F2",
            margin=dict(t=20, b=10),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with ch2:
        st.markdown("#### Benford's Law — Dataset Analysis")
        bsummary = st.session_state.benford_summary
        if bsummary:
            digits = bsummary["digits"]
            observed = bsummary["observed_freq"]
            expected = bsummary["expected_probs"]
            p_val = bsummary["p_value"]
            interpretation = bsummary["interpretation"]
            severity = bsummary["severity"]

            fig_benford = go.Figure()
            fig_benford.add_trace(go.Bar(
                x=digits,
                y=[o * 100 for o in observed],
                name="Observed",
                marker_color="#0B2545",
                opacity=0.7,
            ))
            fig_benford.add_trace(go.Scatter(
                x=digits,
                y=[e * 100 for e in expected],
                name="Benford Expected",
                mode="lines+markers",
                line=dict(color="#C9A961", width=2, dash="dash"),
                marker=dict(size=6),
            ))
            fig_benford.update_layout(
                xaxis=dict(title="First Digit", tickvals=digits),
                yaxis=dict(title="Frequency (%)"),
                template="plotly_white",
                plot_bgcolor="#F7F6F2",
                paper_bgcolor="#F7F6F2",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=30, b=10),
            )
            st.plotly_chart(fig_benford, use_container_width=True)

            insight_colors = {
                "high": ("#fde8e8", "#7f1d1d", "⚠️"),
                "medium": ("#fef3c7", "#78350f", "⚡"),
                "low": ("#d1fae5", "#064e3b", "✅"),
            }
            bg, fg, icon = insight_colors.get(severity, ("#f3f4f6", "#1f2937", "ℹ️"))
            p_display = f"{p_val:.4f}" if p_val >= 0.0001 else f"{p_val:.2e}"
            st.markdown(
                f'<div style="background:{bg};color:{fg};border-radius:6px;padding:10px 14px;'
                f'font-size:0.85rem;margin-top:-8px;">'
                f'{icon} <strong>Dataset Benford p-value: {p_display}</strong> — {interpretation} '
                f'(n={bsummary["n"]:,} invoices analyzed). '
                f'Note: Benford\'s Law is a dataset-level indicator only; individual rows are not flagged for this.'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Flagged Transactions Table ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### Flagged Transactions")

    # Filter controls
    fc1, fc2, fc3 = st.columns([3, 2, 2])
    with fc1:
        cats = ["All"] + sorted(df_flagged["flag_category"].unique().tolist())
        sel_cat = st.selectbox("Filter by category", cats, key="cat_filter")
    with fc2:
        risks = ["All", "High", "Medium", "Low"]
        sel_risk = st.selectbox("Filter by risk level", risks, key="risk_filter")
    with fc3:
        sort_by = st.selectbox("Sort by", ["amount", "posting_date", "vendor_name"], key="sort_by")

    df_view = df_flagged.copy()
    if sel_cat != "All":
        df_view = df_view[df_view["flag_category"] == sel_cat]
    if sel_risk != "All":
        df_view = df_view[df_view["risk_level"] == sel_risk]
    df_view = df_view.sort_values(sort_by, ascending=(sort_by != "amount"))

    display_cols = [
        "transaction_id", "vendor_name", "invoice_number",
        "invoice_date", "posting_date", "amount", "currency",
        "flag_category", "risk_level",
    ]
    available_display = [c for c in display_cols if c in df_view.columns]

    st.dataframe(
        df_view[available_display].reset_index(drop=True),
        use_container_width=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "transaction_id": "Transaction ID",
            "vendor_name": "Vendor",
            "invoice_number": "Invoice #",
            "invoice_date": "Invoice Date",
            "posting_date": "Posting Date",
            "currency": "Currency",
            "flag_category": "Flag Category",
            "risk_level": "Risk Level",
        },
        height=360,
    )

    st.markdown(f"*Showing {len(df_view):,} of {len(df_flagged):,} flagged transactions*")

    # ── Top 10 Highest-Risk ──────────────────────────────────────────────────
    st.markdown("#### Top 10 Highest-Risk Transactions by Dollar Value")
    top10 = (
        df_flagged[df_flagged["risk_level"] == "High"]
        .nlargest(10, "amount")
        [["transaction_id", "vendor_name", "invoice_number", "amount", "flag_category"]]
    )
    if not top10.empty:
        st.dataframe(
            top10.reset_index(drop=True),
            use_container_width=True,
            column_config={"amount": st.column_config.NumberColumn("Amount", format="$%.2f")},
        )
    else:
        st.info("No high-risk transactions found with current filters.")

    # ── AI Memo Generator ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### AI Audit Memo Generator")

    api_key_present = bool(os.environ.get("ANTHROPIC_API_KEY", ""))
    if not api_key_present:
        st.info(
            "🤖 **AI memos require an Anthropic API key.** "
            "Add `ANTHROPIC_API_KEY` to your Replit Secrets (Tools → Secrets) to enable. "
            "All forensic rules run without it."
        )

    generate_memos_toggle = st.toggle(
        "Generate AI Audit Memos with Claude",
        value=False,
        help="Sends each flagged transaction to Claude for a 3-sentence audit memo citing the relevant standard.",
    )

    if generate_memos_toggle:
        if not api_key_present:
            st.warning("ANTHROPIC_API_KEY not configured. Memos will show a setup message.")

        flagged_rows = df_flagged.to_dict("records")
        total = len(flagged_rows)
        progress_bar = st.progress(0, text="Generating memos…")

        for i, row in enumerate(flagged_rows):
            tid = row.get("transaction_id", str(i))
            if tid not in st.session_state.ai_memos:
                with st.spinner(f"Generating memo for {tid} ({i+1}/{total})…"):
                    memo = generate_memo(
                        transaction_id=tid,
                        transaction_json=json.dumps({k: str(v) for k, v in row.items()}),
                        flag_category=row.get("flag_category", ""),
                    )
                    st.session_state.ai_memos[tid] = memo
            progress_bar.progress((i + 1) / total, text=f"Memo {i+1}/{total} complete")

        progress_bar.empty()
        st.success(f"✓ {total} memos generated.")

    if st.session_state.ai_memos:
        st.markdown("**Generated Memos:**")
        for tid, memo in list(st.session_state.ai_memos.items())[:5]:
            row_data = df_flagged[df_flagged["transaction_id"] == tid]
            if not row_data.empty:
                vendor = row_data.iloc[0]["vendor_name"]
                cat = row_data.iloc[0]["flag_category"]
                with st.expander(f"{tid} — {vendor} ({cat})"):
                    st.markdown(memo)
        if len(st.session_state.ai_memos) > 5:
            st.info(f"+ {len(st.session_state.ai_memos) - 5} more memos (see Export Workpaper for full list).")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 — EXPORT WORKPAPER
# ════════════════════════════════════════════════════════════════════════════
elif page == "Export Workpaper":
    st.markdown("""
    <div class="main-header">
      <h1>🔍 AuditCopilot</h1>
      <p>Export Workpaper — Download your audit-ready Excel workpaper</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.audit_run or st.session_state.df_raw is None:
        st.warning("No audit data loaded. Run an audit first.")
        if st.button("🚀 Load Demo Data"):
            load_demo_data()
        st.stop()

    df_all = st.session_state.df_raw
    df_flagged = st.session_state.df_flagged
    memos = st.session_state.ai_memos

    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown("### Workpaper Preview")
        st.markdown("""
        Your Excel workpaper contains three tabs:

        | Tab | Contents |
        |-----|----------|
        | **Summary** | KPI overview, flag category breakdown, generation metadata |
        | **Flagged Transactions** | All flagged rows with risk-level color coding and rule explanations |
        | **AI Memos** | Claude-generated audit memos (if generated) |
        """)

        st.markdown("**Summary Statistics**")
        s1, s2, s3 = st.columns(3)
        s1.metric("Total Transactions", f"{len(df_all):,}")
        s2.metric("Flagged Rows", f"{len(df_flagged):,}")
        s3.metric("AI Memos", f"{len(memos):,}")

        if df_flagged is not None and not df_flagged.empty:
            cat_summary = (
                df_flagged.groupby("flag_category")
                .agg(count=("transaction_id", "count"), total_amount=("amount", "sum"))
                .reset_index()
                .rename(columns={"flag_category": "Category", "count": "Flags", "total_amount": "$ at Risk"})
            )
            st.dataframe(
                cat_summary,
                use_container_width=True,
                column_config={"$ at Risk": st.column_config.NumberColumn(format="$%.2f")},
            )

    with col2:
        st.markdown("### Download")
        st.markdown("""
        Click below to generate and download your workpaper as a formatted Excel file.

        The file is formatted with:
        - Navy/gold header rows
        - Risk-level color coding (red/amber/green)
        - Frozen header rows
        - Auto-sized columns
        - Professional Calibri font
        """)

        if st.button("⬇️ Generate & Download Workpaper", type="primary", use_container_width=True):
            with st.spinner("Building Excel workpaper…"):
                buf = build_workpaper(df_all, df_flagged if df_flagged is not None else pd.DataFrame(), memos)
            st.download_button(
                label="📥 Click to Download AuditCopilot_Workpaper.xlsx",
                data=buf,
                file_name="AuditCopilot_Workpaper.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )
            st.toast("✅ Workpaper exported successfully!")

        st.markdown("---")
        st.markdown("### What's in this file?")
        st.markdown("""
        **Tab 1 — Summary**
        Executive overview with KPI metrics and flag category breakdown.
        Suitable for inclusion in a management memo.

        **Tab 2 — Flagged Transactions**
        All flagged transactions with rule explanations, color-coded by risk level.
        Each row includes the specific rule logic that triggered the flag.

        **Tab 3 — AI Memos**
        If AI memos were generated, each memo cites the relevant auditing standard
        (AU-C 240, AU-C 315, or IAS 21) and recommends a specific testing procedure.
        """)

    st.markdown("""
    <footer>AuditCopilot · Built by Bhoomika Bothra · CA, ICAI ·
    Standards: AU-C 240 · AU-C 315 · IAS 21</footer>
    """, unsafe_allow_html=True)
