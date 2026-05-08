import os
import traceback
import streamlit as st

SYSTEM_PROMPT = (
    "You are a senior internal auditor at a healthcare distribution company. "
    "Given a flagged AP transaction and the rule that flagged it, write a 3-sentence "
    "audit memo citing the relevant auditing standard (AU-C 240 for fraud, AU-C 315 "
    "for risk, IAS 21 for FX) and recommending one specific testing procedure. "
    "Be concise and use professional audit language."
)

STANDARD_MAPPING = {
    "Duplicate Vendor": "AU-C 240",
    "Benford's Law Violation": "AU-C 315",
    "Round-Dollar Payment": "AU-C 240",
    "Weekend Posting": "AU-C 240",
    "Split-PO Pattern": "AU-C 240",
    "FX Misallocation": "IAS 21",
    "Duplicate Invoice Number": "AU-C 240",
}


def _build_prompt(transaction_dict: dict, flag_category: str) -> str:
    standard = STANDARD_MAPPING.get(flag_category, "AU-C 240")
    # Explicitly cast amount to float — it may arrive as a string from JSON serialisation
    try:
        amount = float(transaction_dict.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0
    lines = [
        f"Flag category: {flag_category}",
        f"Relevant standard: {standard}",
        f"Transaction ID: {transaction_dict.get('transaction_id', 'N/A')}",
        f"Vendor: {transaction_dict.get('vendor_name', 'N/A')}",
        f"Invoice number: {transaction_dict.get('invoice_number', 'N/A')}",
        f"Amount: ${amount:,.2f}",
        f"Currency: {transaction_dict.get('currency', 'N/A')}",
        f"Invoice date: {transaction_dict.get('invoice_date', 'N/A')}",
        f"Posting date: {transaction_dict.get('posting_date', 'N/A')}",
        f"GL account: {transaction_dict.get('gl_account', 'N/A')}",
        f"Rule explanation: {transaction_dict.get('rule_explanation', 'N/A')}",
    ]
    return "\n".join(lines)


@st.cache_data(show_spinner=False)
def generate_memo(transaction_id: str, transaction_json: str, flag_category: str) -> str:
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return (
                "⚠️ **AI memos disabled** — add your `ANTHROPIC_API_KEY` in the "
                "Secrets panel (Tools → Secrets) to enable AI-generated audit memos."
            )

        import json
        transaction_dict = json.loads(transaction_json)

        try:
            import anthropic
        except ImportError:
            return (
                "⚠️ **anthropic package not installed.** "
                "Run `pip install anthropic` and restart the app."
            )

        client = anthropic.Anthropic(api_key=api_key)
        user_content = _build_prompt(transaction_dict, flag_category)
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return message.content[0].text

    except Exception as e:
        traceback.print_exc()
        return f"⚠️ **AI memo generation failed:** {str(e)}"
