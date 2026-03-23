"""
dashboard.py  –  Microservice 3: Prior Authorization Dashboard
===============================================================
Enterprise-grade, Human-in-the-Loop SaaS dashboard.
Dark themed, sidebar controls, filtered queue, and Executive
Analytics view.

Run:
    streamlit run dashboard.py
"""

import os
import io
import sys
import json
import glob
import subprocess
from datetime import datetime

import streamlit as st
import pandas as pd
import plotly.express as px

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Command Center",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide Streamlit default UI — keep sidebar toggle visible */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    header[data-testid="stHeader"] .stDeployButton,
    header[data-testid="stHeader"] #MainMenu {
        display: none !important;
    }

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

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background-color: #131825 !important;
        border-right: 1px solid #2d3748;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #e2e8f0 !important;
    }
    .sidebar-brand {
        font-size: 22px;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        letter-spacing: -0.3px;
    }
    .sidebar-divider {
        border: 0;
        border-top: 1px solid #2d3748;
        margin: 18px 0;
    }
    .sidebar-section-label {
        font-size: 11px;
        font-weight: 700;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
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

    /* ── Tab Styling ── */
    div[data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #161b27;
        border-radius: 12px;
        padding: 6px;
    }
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #1e2535 !important;
        color: #60a5fa !important;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: #60a5fa !important;
        border-radius: 4px;
    }
    div[data-baseweb="tab-border"] {
        display: none !important;
    }

    /* ── Executive Dashboard Cards ── */
    .exec-metric-card {
        background: linear-gradient(135deg, #1a2540 0%, #1e2d4a 100%);
        border: 1px solid #2d3748;
        border-radius: 16px;
        padding: 28px 24px;
        text-align: center;
    }
    .exec-metric-value {
        font-size: 48px;
        font-weight: 800;
        letter-spacing: -1px;
        margin-bottom: 4px;
    }
    .exec-metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #94a3b8 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .exec-section-title {
        font-size: 18px;
        font-weight: 700;
        color: #e2e8f0 !important;
        margin-top: 30px;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid #2d3748;
    }

    /* ── Filtered results count badge ── */
    .filter-badge {
        display: inline-block;
        background: #1e2535;
        border: 1px solid #2d3748;
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 16px;
    }
    .filter-badge strong {
        color: #60a5fa !important;
    }

    /* ── Audit Trail Timeline ── */
    .audit-timeline {
        border-left: 2px solid #2d3748;
        margin-left: 8px;
        padding-left: 16px;
        margin-top: 8px;
    }
    .audit-entry {
        position: relative;
        margin-bottom: 12px;
        font-size: 13px;
        color: #cbd5e1;
        line-height: 1.5;
    }
    .audit-entry::before {
        content: '';
        position: absolute;
        left: -21px;
        top: 6px;
        width: 8px;
        height: 8px;
        background: #3b82f6;
        border-radius: 50%;
        border: 2px solid #0f1117;
    }

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & UTILS
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR   = os.path.join(BASE_DIR, "processed_results")

def load_results() -> list:
    """Load all processed result JSONs, enriched with file metadata."""
    if not os.path.exists(RESULTS_DIR):
        return []
        
    files = glob.glob(os.path.join(RESULTS_DIR, "*.json"))
    data_list = []

    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
                d["_file_path"] = fp
                # Derive a sortable timestamp — prefer JSON field, fallback to OS mtime
                ts = d.get("adjudication_timestamp", "")
                if not ts:
                    ts = datetime.fromtimestamp(os.path.getmtime(fp)).isoformat()
                d["_sort_timestamp"] = ts
                # Pre-compute patient full name for search / sort
                pat = d.get("patient", {})
                d["_full_name"] = f"{pat.get('first_name', '')} {pat.get('last_name', '')}".strip()
                # Determine effective display status
                adj = d.get("adjudication", {})
                reason = adj.get("reason_message", "")
                if "[HUMAN OVERRIDE]" in reason:
                    d["_display_status"] = "OVERRIDDEN"
                else:
                    d["_display_status"] = adj.get("status", "PENDING")

                # ── Audit Trail: initialize baseline if missing ──
                if "audit_log" not in d:
                    adj_status = adj.get("status", "UNKNOWN")
                    adj_reason = adj.get("reason_message", "No reason")
                    # Use the adjudication timestamp or file mtime for the baseline date
                    baseline_ts = d.get("adjudication_timestamp", "")
                    if baseline_ts:
                        try:
                            baseline_dt = datetime.fromisoformat(baseline_ts).strftime("%Y-%m-%d %H:%M:%S")
                        except Exception:
                            baseline_dt = baseline_ts[:19]
                    else:
                        baseline_dt = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M:%S")
                    d["audit_log"] = [
                        f"\U0001f534 [{baseline_dt}]: AI Initial Decision - {adj_status} (Reason: {adj_reason})"
                    ]

                data_list.append(d)
        except Exception:
            pass

    # Default sort: newest first
    data_list.sort(key=lambda x: x["_sort_timestamp"], reverse=True)
    return data_list

def override_status(file_path: str, new_status: str, claim_id: str):
    """Action handler to update a JSON file with manual override + audit trail."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        old_status = data.get("adjudication", {}).get("status", "UNKNOWN")
        old_reason = data.get("adjudication", {}).get("reason_message", "")
        old_adj_ts = data.get("adjudication_timestamp", "")   # capture BEFORE overwrite
        override_text = f"[HUMAN OVERRIDE] from {old_status} to {new_status}"
        
        if "adjudication" not in data:
            data["adjudication"] = {}
        
        data["adjudication"]["status"] = new_status
        
        if "[HUMAN OVERRIDE]" not in old_reason:
            data["adjudication"]["reason_message"] = f"{override_text} - {old_reason}"
        else:
            data["adjudication"]["reason_message"] = f"{override_text}"

        now_ts = datetime.now()
        data["adjudication_timestamp"] = now_ts.isoformat()

        # ── Audit Trail: seed baseline if missing, then append override ──
        if "audit_log" not in data:
            # Reconstruct the original AI decision as the baseline entry
            if old_adj_ts:
                try:
                    baseline_dt = datetime.fromisoformat(old_adj_ts).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    baseline_dt = old_adj_ts[:19]
            else:
                baseline_dt = now_ts.strftime("%Y-%m-%d %H:%M:%S")
            orig_reason = old_reason if old_reason else "No reason"
            data["audit_log"] = [
                f"\U0001f534 [{baseline_dt}]: AI Initial Decision - {old_status} (Reason: {orig_reason})"
            ]
        ts_str = now_ts.strftime("%Y-%m-%d %H:%M:%S")
        if new_status == "APPROVED":
            audit_icon = "\U0001f7e2"  # green circle
        else:
            audit_icon = "\U0001f534"  # red circle
        data["audit_log"].append(
            f"{audit_icon} [{ts_str}]: Human Override to {new_status} (User: Clinical Reviewer)"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        st.toast(f"Claim {claim_id} manually updated to {new_status}!", icon="✨")
        st.rerun()

    except Exception as e:
        st.error(f"Failed to update {file_path}: {e}")

def build_csv(items: list) -> str:
    """Build a CSV string from a list of result dicts."""
    rows = []
    for d in items:
        pat = d.get("patient", {})
        adj = d.get("adjudication", {})
        req = d.get("request", {})
        rows.append({
            "Member ID":    pat.get("member_id", ""),
            "Patient Name": d.get("_full_name", ""),
            "Diagnosis":    pat.get("diagnosis_code", ""),
            "CPT Code":     req.get("cpt_code", ""),
            "Physio Days":  req.get("physio_days", ""),
            "Status":       adj.get("status", ""),
            "Display Status": d.get("_display_status", ""),
            "Reason":       adj.get("reason_message", ""),
            "Timestamp":    d.get("_sort_timestamp", ""),
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA (global — before any UI)
# ─────────────────────────────────────────────────────────────────────────────

data_list = load_results()

# ── Global KPI counters (always reflect ALL data, not filtered) ──
total_reqs     = len(data_list)
ai_approved    = 0
ai_rejected    = 0
ai_pended      = 0
override_count = 0
stp_count      = 0

for d in data_list:
    ds = d.get("_display_status", "")
    if ds == "OVERRIDDEN":
        override_count += 1
    elif ds == "APPROVED":
        ai_approved += 1
        stp_count += 1
    elif ds == "REJECTED":
        ai_rejected += 1
        stp_count += 1
    elif ds == "PENDING":
        ai_pended += 1


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Queue Controls
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="sidebar-brand">⚙️ Queue Controls</div>', unsafe_allow_html=True)
    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    # Refresh
    if st.button("🔄  Refresh Data", use_container_width=True):
        st.rerun()

    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    # ── AI Processing Engine Trigger ──
    st.markdown('<div class="sidebar-section-label">Processing Engine</div>', unsafe_allow_html=True)
    if st.button("▶️  Run AI Processing Engine", use_container_width=True):
        with st.spinner("AI Engine processing new documents and generating EDI 278 payload..."):
            python_exe = sys.executable
            scripts = ["intake_engine.py", "validation_engine.py", "rules_engine.py"]
            for script in scripts:
                script_path = os.path.join(BASE_DIR, script)
                if os.path.isfile(script_path):
                    subprocess.run([python_exe, script_path], cwd=BASE_DIR)
        st.success("Processing Complete")
        st.toast("AI Processing Engine finished successfully!", icon="✅")
        st.rerun()

    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    # Search
    st.markdown('<div class="sidebar-section-label">Search</div>', unsafe_allow_html=True)
    search_query = st.text_input(
        "🔍  Search",
        placeholder="Patient name or Member ID…",
        label_visibility="collapsed",
    )

    st.write("")  # spacer

    # Status filter
    st.markdown('<div class="sidebar-section-label">Filter by Status</div>', unsafe_allow_html=True)
    status_filter = st.multiselect(
        "Filter by Status",
        options=["APPROVED", "REJECTED", "PENDING", "OVERRIDDEN"],
        default=[],
        label_visibility="collapsed",
    )

    st.write("")

    # Sort
    st.markdown('<div class="sidebar-section-label">Sort Order</div>', unsafe_allow_html=True)
    sort_option = st.selectbox(
        "Sort by",
        options=["Newest First", "Oldest First", "Patient Name (A-Z)"],
        label_visibility="collapsed",
    )

    st.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

    # ── CSV Download (placed at the bottom, will use filtered list) ──
    # Placeholder — the actual download button is rendered after filtering below


# ─────────────────────────────────────────────────────────────────────────────
# APPLY FILTERS & SORT
# ─────────────────────────────────────────────────────────────────────────────

filtered_list = list(data_list)  # shallow copy

# Search
if search_query:
    q = search_query.strip().upper()
    filtered_list = [
        d for d in filtered_list
        if q in d.get("_full_name", "").upper()
        or q in d.get("patient", {}).get("member_id", "").upper()
    ]

# Status filter
if status_filter:
    filtered_list = [
        d for d in filtered_list
        if d.get("_display_status", "") in status_filter
    ]

# Sort
if sort_option == "Newest First":
    filtered_list.sort(key=lambda x: x["_sort_timestamp"], reverse=True)
elif sort_option == "Oldest First":
    filtered_list.sort(key=lambda x: x["_sort_timestamp"], reverse=False)
elif sort_option == "Patient Name (A-Z)":
    filtered_list.sort(key=lambda x: x.get("_full_name", "").upper())

# ── Now render the CSV download in the sidebar with the filtered data ──
with st.sidebar:
    csv_data = build_csv(filtered_list)
    st.download_button(
        label="📥  Download Filtered Report (CSV)",
        data=csv_data,
        file_name=f"prior_auth_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<div class="enterprise-title">Command Center</div>', unsafe_allow_html=True)
st.markdown('<div class="enterprise-subtitle">Human-in-the-Loop Prior Authorization Engine · Dark Theme</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2 = st.tabs(["🩺 Clinical Queue", "📊 Executive Dashboard"])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — CLINICAL QUEUE
# ═══════════════════════════════════════════════════════════════════════════

with tab1:

    # ── KPI METRICS (global totals, not filtered) ──
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"**Total Requests**<br><span style='font-size: 36px; font-weight: bold; color: #f8fafc;'>{total_reqs}</span>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"**AI Auto-Approved**<br><span style='font-size: 36px; font-weight: bold; color: #34d399;'>{ai_approved}</span>", unsafe_allow_html=True)

    with col3:
        st.markdown(f"**AI Rejected**<br><span style='font-size: 36px; font-weight: bold; color: #f87171;'>{ai_rejected}</span>", unsafe_allow_html=True)

    with col4:
        st.markdown(f"**Human Overrides**<br><span style='font-size: 36px; font-weight: bold; color: #fbbf24;'>{override_count}</span>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #2d3748; margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # ── Filter results badge ──
    if search_query or status_filter:
        st.markdown(
            f'<div class="filter-badge">Showing <strong>{len(filtered_list)}</strong> of {total_reqs} requests</div>',
            unsafe_allow_html=True,
        )

    # ── REQUESTS QUEUE (filtered + sorted) ──
    if not filtered_list:
        if search_query or status_filter:
            st.warning("No requests match your current filters. Adjust the sidebar controls to see results.")
        else:
            st.info("No processed requests found. Drop files into `/processed_results` to see them here.")
    else:
        for idx, item in enumerate(filtered_list):
            pat = item.get("patient", {})
            adj = item.get("adjudication", {})
            req = item.get("request", {})

            mem_id       = pat.get("member_id", "UNKNOWN")
            raw_status   = adj.get("status", "UNKNOWN")
            disp_status  = item.get("_display_status", raw_status)
            full_name    = item.get("_full_name", "Unknown")
            fp           = item.get("_file_path")

            # ── Upgraded expander label ──
            icon = {"APPROVED": "✅", "REJECTED": "❌", "OVERRIDDEN": "🔄", "PENDING": "⏳"}.get(disp_status, "❓")
            expander_title = f"📄 {full_name}  |  ID: {mem_id}  |  Status: {disp_status} {icon}"

            with st.expander(expander_title, expanded=False):
                left_col, right_col = st.columns([1.6, 1], gap="large")

                # ═══════ LEFT COLUMN — Evidence & Extracted Data ═══════
                with left_col:
                    # Source Evidence / Clinical notes
                    st.markdown('<div class="expander-subheader">Source Evidence (XAI)</div>', unsafe_allow_html=True)
                    evidence = req.get("source_evidence", None)
                    if evidence:
                        st.markdown(f'<div class="evidence-box">"{evidence}"</div>', unsafe_allow_html=True)
                    else:
                        st.info("No source evidence extracted for this request.")

                    # Structured data table
                    st.markdown('<div class="expander-subheader">Extracted Variables</div>', unsafe_allow_html=True)

                    diagnosis = pat.get("diagnosis_code", "—")
                    cpt_code  = req.get("cpt_code", "—")
                    days      = req.get("physio_days", "—")

                    table_html = f"""
                    <table class="kv-table">
                        <tr><td class="kv-key">Patient Name</td><td class="kv-val">{full_name}</td></tr>
                        <tr><td class="kv-key">Member ID</td><td class="kv-val">{mem_id}</td></tr>
                        <tr><td class="kv-key">Diagnosis Code</td><td class="kv-val">{diagnosis}</td></tr>
                        <tr><td class="kv-key">Requested CPT</td><td class="kv-val">{cpt_code}</td></tr>
                        <tr><td class="kv-key">Physio Days</td><td class="kv-val">{days}</td></tr>
                    </table>
                    """
                    st.markdown(table_html, unsafe_allow_html=True)

                # ═══════ RIGHT COLUMN — AI Reasoning & Actions ═══════
                with right_col:
                    st.markdown('<div class="expander-subheader">AI Reasoning</div>', unsafe_allow_html=True)

                    reason_msg = adj.get("reason_message", "No reason provided")
                    if raw_status == "REJECTED":
                        st.markdown(f'<div class="reason-box-rejected">{reason_msg}</div>', unsafe_allow_html=True)
                    elif raw_status == "APPROVED":
                        st.markdown(f'<div class="reason-box-approved">{reason_msg}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="reason-box-pending">{reason_msg}</div>', unsafe_allow_html=True)

                    # CPT badge
                    policy = adj.get("policy_applied", "")
                    if policy:
                        st.markdown(f"<span style='font-size:12px; color:#94a3b8;'>Policy: <strong style=\"color:#e2e8f0\">{policy}</strong></span>", unsafe_allow_html=True)

                    st.write("")  # spacer

                    st.markdown('<div class="expander-subheader">Action Panel</div>', unsafe_allow_html=True)
                    st.markdown("""
                    <div style="font-size: 13px; color: #94a3b8; margin-bottom: 12px;">
                        Review the extraction on the left before overriding.
                    </div>
                    """, unsafe_allow_html=True)

                    if raw_status == "REJECTED" or raw_status == "PENDING":
                        if st.button("✅ Force Approve", key=f"app_{idx}", type="primary", use_container_width=True):
                            override_status(fp, "APPROVED", mem_id)

                    if raw_status == "APPROVED" or raw_status == "PENDING":
                        if st.button("❌ Manual Reject", key=f"rej_{idx}", type="secondary", use_container_width=True):
                            override_status(fp, "REJECTED", mem_id)

                # ═══════ AUDIT TRAIL (full-width, below both columns) ═══════
                st.markdown('<div class="expander-subheader">📝 Audit Trail & Timeline</div>', unsafe_allow_html=True)
                audit_log = item.get("audit_log", [])
                if audit_log:
                    timeline_html = '<div class="audit-timeline">'
                    for entry in audit_log:
                        timeline_html += f'<div class="audit-entry">{entry}</div>'
                    timeline_html += '</div>'
                    st.markdown(timeline_html, unsafe_allow_html=True)
                else:
                    st.caption("No audit events recorded.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — EXECUTIVE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

with tab2:

    st.markdown('<div class="exec-section-title">📈 Key Performance Indicators</div>', unsafe_allow_html=True)

    # ── KPI Metrics Row ──
    rn_hours_saved = round(total_reqs * 20 / 60, 1)   # 20 min per request
    stp_rate = round((stp_count / total_reqs) * 100, 1) if total_reqs > 0 else 0.0

    kpi1, kpi2, kpi3 = st.columns(3)

    with kpi1:
        st.markdown(f"""
        <div class="exec-metric-card">
            <div class="exec-metric-value" style="color: #60a5fa;">{total_reqs}</div>
            <div class="exec-metric-label">Total Requests Processed</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="exec-metric-card">
            <div class="exec-metric-value" style="color: #34d399;">{rn_hours_saved} hrs</div>
            <div class="exec-metric-label">Est. RN Hours Saved (20 min/req)</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="exec-metric-card">
            <div class="exec-metric-value" style="color: #fbbf24;">{stp_rate}%</div>
            <div class="exec-metric-label">Straight-Through Processing Rate</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")  # spacer

    # ── Charts Row ──
    st.markdown('<div class="exec-section-title">📊 Adjudication Outcome Breakdown</div>', unsafe_allow_html=True)

    chart_left, chart_right = st.columns(2, gap="large")

    status_counts = {"Approved": 0, "Rejected": 0, "Pended": 0}
    for d in data_list:
        s = d.get("adjudication", {}).get("status", "")
        if s == "APPROVED":
            status_counts["Approved"] += 1
        elif s == "REJECTED":
            status_counts["Rejected"] += 1
        else:
            status_counts["Pended"] += 1

    chart_df = pd.DataFrame({
        "Status": list(status_counts.keys()),
        "Count":  list(status_counts.values()),
    })

    color_map = {"Approved": "#34d399", "Rejected": "#f87171", "Pended": "#fbbf24"}

    with chart_left:
        st.bar_chart(
            chart_df.set_index("Status"),
            color="#60a5fa",
            use_container_width=True,
        )

    with chart_right:
        fig = px.pie(
            chart_df,
            names="Status",
            values="Count",
            hole=0.45,
            color="Status",
            color_discrete_map=color_map,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", color="#e2e8f0", size=14),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
                font=dict(size=13),
            ),
            margin=dict(t=20, b=40, l=20, r=20),
        )
        fig.update_traces(
            textinfo="label+percent",
            textfont_size=14,
            marker=dict(line=dict(color="#0f1117", width=2)),
        )
        st.plotly_chart(fig, use_container_width=True)
