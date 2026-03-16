"""
dashboard.py  –  Microservice 3: Prior Authorization Dashboard
===============================================================
Modern, Human-in-the-Loop SaaS dashboard with expander view.
Dark themed, rich UI with proper text visibility and extracted
data tables.

Run:
    streamlit run dashboard.py
"""

import os
import json
import glob
from datetime import datetime

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Command Center",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide Streamlit default UI */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Global font & base ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp { 
        font-family: 'Inter', sans-serif !important; 
    }

    /* ── Dark Theme Overrides & Visibility ── */
    .stApp {
        background-color: #0f1117 !important;
        color: #e2e8f0 !important;
    }
    h1, h2, h3, p, span {
        color: #e2e8f0 !important;
    }

    /* ── Enterprise Title ── */
    .enterprise-title {
        font-size: 32px;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
        letter-spacing: -0.5px;
    }
    .enterprise-subtitle {
        font-size: 15px;
        color: #94a3b8 !important;
        margin-bottom: 30px;
    }

    /* ── KPI Metrics ── */
    div[data-testid="stMetricValue"] {
        font-size: 36px !important;
        font-weight: 700 !important;
        color: #f8fafc !important;
    }
    div[data-testid="stMetricLabel"] p {
        font-size: 14px !important;
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] details summary,
    [data-testid="stExpander"] details summary:hover,
    [data-testid="stExpander"] details summary:focus,
    [data-testid="stExpander"] details summary:active {
        font-size: 16px !important;
        font-weight: 600 !important;
        background-color: #1a2540 !important;
        border-radius: 8px !important;
        color: #e2e8f0 !important;
    }
    .stExpander {
        background-color: #1e2535 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 10px !important;
        margin-bottom: 12px !important;
    }

    /* ── Tables for Extracted Data ── */
    .kv-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 20px;
        background-color: #161b27;
        border-radius: 8px;
        overflow: hidden;
    }
    .kv-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #2d3748;
        font-size: 14px;
        color: #e2e8f0;
    }
    .kv-key {
        color: #94a3b8 !important;
        font-weight: 500;
        width: 35%;
        background-color: #1e2535;
    }
    .kv-val {
        font-weight: 600;
    }

    /* ── Custom Callout Boxes ── */
    .reason-box-rejected {
        background: #200d0d;
        border-left: 4px solid #ef4444;
        padding: 12px 16px;
        border-radius: 0 4px 4px 0;
        color: #ffffff;
        margin-bottom: 16px;
    }
    .reason-box-approved {
        background: #0d2018;
        border-left: 4px solid #10b981;
        padding: 12px 16px;
        border-radius: 0 4px 4px 0;
        color: #ffffff;
        margin-bottom: 16px;
    }
    .reason-box-pending {
        background: #1e1a0d;
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        border-radius: 0 4px 4px 0;
        color: #ffffff;
        margin-bottom: 16px;
    }
    
    .evidence-box {
        background: linear-gradient(135deg, #1a2332 0%, #1c2a3a 100%);
        border-left: 4px solid #3b82f6;
        padding: 14px 18px;
        color: #ffffff;
        font-style: italic;
        margin-bottom: 16px;
        border-radius: 0 4px 4px 0;
    }

    /* ── Override Buttons (target via Streamlit type) ── */
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: #059669 !important; /* Green */
        color: white !important;
        border: 1px solid #047857 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #047857 !important;
        border-color: #065f46 !important;
    }
    div[data-testid="stButton"] > button[kind="primary"] p,
    div[data-testid="stButton"] > button[kind="primary"] div {
        color: white !important;
    }

    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: #ef4444 !important; /* Red */
        color: white !important;
        border: 1px solid #b91c1c !important;
        font-weight: 600 !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: #dc2626 !important;
        border-color: #991b1b !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"] p,
    div[data-testid="stButton"] > button[kind="secondary"] div {
        color: white !important;
    }

    /* Subheaders inside expanders */
    .expander-subheader {
        font-size: 14px;
        font-weight: 600;
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 10px;
        margin-bottom: 8px;
        border-bottom: 1px solid #2d3748;
        padding-bottom: 4px;
    }

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & UTILS
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR   = os.path.join(BASE_DIR, "processed_results")

def load_results() -> list:
    """Load all processed result JSONs directly."""
    if not os.path.exists(RESULTS_DIR):
        return []
        
    files = glob.glob(os.path.join(RESULTS_DIR, "*.json"))
    data_list = []

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
                d["_file_path"] = fp # Store path for easy saving
                data_list.append(d)
        except Exception:
            pass

    # Sort by timestamp, newest first
    data_list.sort(
        key=lambda x: x.get("adjudication_timestamp", ""), 
        reverse=True
    )
    return data_list

def override_status(file_path: str, new_status: str, claim_id: str):
    """Action handler to update a JSON file with manual override."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Determine the override reason prefix
        old_status = data.get("adjudication", {}).get("status", "UNKNOWN")
        override_text = f"[HUMAN OVERRIDE] from {old_status} to {new_status}"
        
        # Update payload
        if "adjudication" not in data:
            data["adjudication"] = {}
        
        data["adjudication"]["status"] = new_status
        
        old_reason = data["adjudication"].get("reason_message", "")
        if "[HUMAN OVERRIDE]" not in old_reason:
            data["adjudication"]["reason_message"] = f"{override_text} - {old_reason}"
        else:
            data["adjudication"]["reason_message"] = f"{override_text}"

        data["adjudication_timestamp"] = datetime.now().isoformat()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        # Show toast notification
        st.toast(f"Claim {claim_id} manually updated to {new_status}!", icon="✨")
        st.rerun()

    except Exception as e:
        st.error(f"Failed to update {file_path}: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="enterprise-title">Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="enterprise-subtitle">Human-in-the-Loop Prior Authorization Engine · Dark Theme</div>', unsafe_allow_html=True)

# ── Load Data
data_list = load_results()

# ─────────────────────────────────────────────────────────────────────────────
# KPI METRICS
# ─────────────────────────────────────────────────────────────────────────────

total_reqs = len(data_list)
ai_approved = 0
ai_rejected = 0
override_count = 0

for d in data_list:
    adj = d.get("adjudication", {})
    status = adj.get("status", "")
    reason = adj.get("reason_message", "")
    
    if "[HUMAN OVERRIDE]" in reason:
        override_count += 1
    elif status == "APPROVED":
        ai_approved += 1
    elif status == "REJECTED":
        ai_rejected += 1

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"**Total Requests**<br><span style='font-size: 36px; font-weight: bold; color: #f8fafc;'>{total_reqs}</span>", unsafe_allow_html=True)

with col2:
    st.markdown(f"**AI Auto-Approved**<br><span style='font-size: 36px; font-weight: bold; color: #34d399;'>{ai_approved}</span>", unsafe_allow_html=True)

with col3:
    st.markdown(f"**AI Rejected**<br><span style='font-size: 36px; font-weight: bold; color: #f87171;'>{ai_rejected}</span>", unsafe_allow_html=True)
    
with col4:
    st.markdown(f"**Human Overrides**<br><span style='font-size: 36px; font-weight: bold; color: #fbbf24;'>{override_count}</span>", unsafe_allow_html=True)

st.markdown("<hr style='border-color: #2d3748; margin-top: 10px; margin-bottom: 30px;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# REQUESTS QUEUE
# ─────────────────────────────────────────────────────────────────────────────

if not data_list:
    st.info("No processed requests found. Drop files into `/processed_results` to see them here.")
else:
    for idx, item in enumerate(data_list):
        pat = item.get("patient", {})
        adj = item.get("adjudication", {})
        req = item.get("request", {})
        
        mem_id = pat.get('member_id', 'UNKNOWN')
        status = adj.get('status', 'UNKNOWN')
        fp = item.get('_file_path')
        
        # Expander Title
        icon = "✅" if status == "APPROVED" else "❌" if status == "REJECTED" else "⏳"
        expander_title = f"{icon} Request: {mem_id} — {pat.get('first_name','')} {pat.get('last_name','')}"
        
        if "[HUMAN OVERRIDE]" in adj.get("reason_message", ""):
           expander_title += " (OVERRIDDEN)"
           
        with st.expander(expander_title, expanded=False):
            left_col, right_col = st.columns([2.5, 1], gap="large")
            
            with left_col:
                # ── AI REASONING ──
                st.markdown('<div class="expander-subheader">Adjudication Reason</div>', unsafe_allow_html=True)
                
                reason_msg = adj.get('reason_message', 'No reason provided')
                if status == "REJECTED":
                    st.markdown(f'<div class="reason-box-rejected">{reason_msg}</div>', unsafe_allow_html=True)
                elif status == "APPROVED":
                    st.markdown(f'<div class="reason-box-approved">{reason_msg}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="reason-box-pending">{reason_msg}</div>', unsafe_allow_html=True)
                    
                # ── SOURCE EVIDENCE ──
                st.markdown('<div class="expander-subheader">Source Evidence (XAI)</div>', unsafe_allow_html=True)
                evidence = req.get('source_evidence', 'No source evidence extracted for this request.')
                st.markdown(f'<div class="evidence-box">"{evidence}"</div>', unsafe_allow_html=True)
                
                # ── STRUCTURED DATA TABLE ──
                st.markdown('<div class="expander-subheader">Extracted Variables</div>', unsafe_allow_html=True)
                
                patient_name = f"{pat.get('first_name','')} {pat.get('last_name','')}"
                diagnosis = pat.get('diagnosis_code', '—')
                cpt_code = req.get('cpt_code', '—')
                days = req.get('physio_days', '—')
                
                table_html = f"""
                <table class="kv-table">
                    <tr><td class="kv-key">Patient Name</td><td class="kv-val">{patient_name}</td></tr>
                    <tr><td class="kv-key">Diagnosis Code</td><td class="kv-val">{diagnosis}</td></tr>
                    <tr><td class="kv-key">Requested CPT</td><td class="kv-val">{cpt_code}</td></tr>
                    <tr><td class="kv-key">Physio Days</td><td class="kv-val">{days}</td></tr>
                </table>
                """
                st.markdown(table_html, unsafe_allow_html=True)
                
            with right_col:
                st.markdown('<div class="expander-subheader">Action Panel</div>', unsafe_allow_html=True)
                st.write("") # spacing
                
                st.markdown("""
                <div style="font-size: 13px; color: #94a3b8; margin-bottom: 12px;">
                    Review the AI extraction on the left carefully before overriding the decision.
                </div>
                """, unsafe_allow_html=True)
                
                if status == "REJECTED" or status == "PENDING":
                    if st.button("Force Approve", key=f"app_{idx}", type="primary", use_container_width=True):
                        override_status(fp, "APPROVED", mem_id)
                
                if status == "APPROVED" or status == "PENDING":
                    if st.button("Manual Reject", key=f"rej_{idx}", type="secondary", use_container_width=True):
                        override_status(fp, "REJECTED", mem_id)
