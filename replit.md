# AuditCopilot

An AI-assisted forensic AP review tool that ingests healthcare accounts payable data, flags anomalies using forensic-accounting rules, and generates auditor-ready workpapers with plain-English risk narratives.

## Run & Operate

- **Start AuditCopilot:** `cd artifacts/audit-copilot && streamlit run main.py --server.port 8080 --server.address 0.0.0.0`
- Workflow name: `AuditCopilot` (auto-configured, runs on port 8080)
- Optional: Add `ANTHROPIC_API_KEY` in Secrets to enable AI memo generation

## Stack

- Python 3.11, Streamlit
- Data: pandas, numpy, scipy, rapidfuzz, plotly, openpyxl
- AI (optional): Anthropic Python SDK (claude-sonnet-4-5)
- No database, no authentication

## Where things live

- `artifacts/audit-copilot/main.py` — Streamlit UI (4 pages)
- `artifacts/audit-copilot/rules.py` — Forensic rule engine (7 rule types)
- `artifacts/audit-copilot/ai_memo.py` — AI memo generator with graceful fallback
- `artifacts/audit-copilot/data_generator.py` — 200+ row synthetic healthcare AP dataset
- `artifacts/audit-copilot/excel_export.py` — Excel workpaper builder (3 tabs)
- `artifacts/audit-copilot/.streamlit/config.toml` — Theme (navy/gold audit palette)
- `artifacts/audit-copilot/requirements.txt` — Python dependencies

## Architecture decisions

- Single-file Streamlit app with sidebar navigation (no routing needed)
- Rule engine is pure Python — no AI required for detection, only for memos
- AI memos use `@st.cache_data` keyed on transaction_id to avoid re-calling the API
- Excel workpaper uses openpyxl directly for full control over formatting
- Synthetic dataset is generated in-memory on each run (no file I/O required)

## Product

- Home page with story banner and "Try Demo Data" one-click flow
- Upload & Run: CSV upload or sample data, then forensic rule engine
- Risk Dashboard: KPI cards, Benford chart, flags-by-category bar, filterable table, AI memo toggle
- Export Workpaper: formatted .xlsx with Summary, Flagged Transactions, AI Memos tabs

## User preferences

- Audit-professional color scheme: navy #0B2545, gold #C9A961
- No React/Next.js — Streamlit only
- Standards cited: AU-C 240, AU-C 315, IAS 21

## Gotchas

- Port 8080 is used by Streamlit; port 5000 is reserved for the api-server artifact
- `ANTHROPIC_API_KEY` must be in Replit Secrets for AI memos (graceful degradation if missing)
- Streamlit config.toml controls both server config and theme — do not split them

## Pointers

- See the `pnpm-workspace` skill for workspace structure info (Node.js side)
