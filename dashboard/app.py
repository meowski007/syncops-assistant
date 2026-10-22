"""
SyncOps Assistant - Customer-Experience Reliability & SRE Triage Dashboard.
Built with Streamlit & Plotly. Connects to FastAPI REST API as single source of truth.
DISCLOSURE: ALL METRICS AND TELEMETRY DISPLAYED ARE DETERMINISTIC SYNTHETIC DATA.
"""

import os
import requests
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="SyncOps Assistant | Customer-Experience Reliability",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# ==============================================================================
# Helper API Functions
# ==============================================================================
def fetch_api(endpoint: str, params: dict | None = None) -> dict | list | None:
    """Safely queries FastAPI backend with connection error handling."""
    url = f"{API_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(url, params=params, timeout=5.0)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            st.warning(f"API returned status {response.status_code} for {endpoint}")
            return None
    except requests.exceptions.RequestException:
        return None

def trigger_triage_api(incident_id: str, force_fallback: bool = True) -> dict | None:
    """Invokes the /triage endpoint."""
    url = f"{API_URL.rstrip('/')}/triage"
    try:
        response = requests.post(
            url,
            json={"incident_id": incident_id, "force_fallback": force_fallback},
            timeout=15.0
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to communicate with triage API: {e}")
        return None

# ==============================================================================
# Header & Synthetic Disclosure Banner
# ==============================================================================
st.markdown("""
<div style="background-color: #1e293b; padding: 16px; border-radius: 8px; border-left: 6px solid #38bdf8; margin-bottom: 20px;">
    <h1 style="color: #f8fafc; margin: 0; font-size: 26px;">🛡️ SyncOps Assistant: Customer-Experience Reliability Platform</h1>
    <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">
        <strong>SRE Workflow: Detect → Explain → Recover → Confirm</strong> |
        <span style="background-color: #334155; color: #fbbf24; padding: 2px 8px; border-radius: 4px; font-weight: bold;">
            SYNTHETIC DATA DISCLOSURE: All telemetry is 100% synthetically generated for educational reliability engineering analysis.
        </span>
    </p>
</div>
""", unsafe_allow_html=True)

# Sidebar Controls
st.sidebar.title("⚙️ Controls & Filters")
window_selection = st.sidebar.selectbox(
    "Calculation Window:",
    options=[("Past 24 Hours", 24), ("Past 7 Days", 168), ("All Time", None)],
    format_func=lambda x: x[0]
)
selected_window_hours = window_selection[1]

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Backend Service")
st.sidebar.code(f"API: {API_URL}", language="text")

# Check Health First
health_data = fetch_api("health")
if not health_data:
    st.error(f"""
    🚨 **Unable to connect to FastAPI backend at `{API_URL}`.**
    
    To start the backend service, open a terminal in the project folder and run:
    ```powershell
    .venv\\Scripts\\uvicorn app.main:app --reload --port 8000
    ```
    """)
    st.stop()

# ==============================================================================
# Platform Status & KPI Cards
# ==============================================================================
kpi_data = fetch_api("kpis", params={"window_hours": selected_window_hours} if selected_window_hours else None)

if kpi_data:
    st.subheader("📈 Customer-Experience Core KPIs")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        s_rate = kpi_data["sync_success_rate"]["value"]
        k1.metric(
            "Sync Success Rate",
            f"{s_rate}%",
            delta=f"{round(s_rate - 95.0, 1)}% vs 95% SLO",
            help="Numerator: Successful syncs | Denominator: Total sync attempts. Why it matters: Measures seamless data continuity for the customer."
        )
    with k2:
        rec_rate = kpi_data["recovery_rate"]["value"]
        k2.metric(
            "Recovery Rate",
            f"{rec_rate}%",
            f"{kpi_data['recovery_rate']['numerator']}/{kpi_data['recovery_rate']['denominator']} Incidents",
            help="Numerator: Mitigated/Resolved incidents | Denominator: Total incidents. Why it matters: Evaluates engineering responsiveness to outages."
        )
    with k3:
        mttr = kpi_data["time_to_recover"]["value"]
        k3.metric(
            "Time to Recover (MTTR)",
            f"{mttr} min",
            help="Mean duration from incident detection to confirmed resolution. Why it matters: Direct indicator of customer downtime duration."
        )
    with k4:
        rpt_rate = kpi_data["repeat_failure_rate"]["value"]
        k4.metric(
            "Repeat Failure Rate",
            f"{rpt_rate}%",
            delta=f"-{rpt_rate}%" if rpt_rate > 5 else "Healthy",
            delta_color="inverse",
            help="Numerator: Customers with >1 failure | Denominator: Impacted customers. Why it matters: Catches recurring customer frustration."
        )

    k5, k6, k7 = st.columns(3)
    with k5:
        tickets = kpi_data["sync_related_support_tickets"]["value"]
        ratio = kpi_data["sync_related_support_tickets"]["ticket_to_failure_ratio"]
        k5.metric(
            "Support Tickets Filed",
            f"{tickets}",
            f"{ratio}% conversion from failures",
            help="Total sync tickets and ticket-to-failure ratio. Why it matters: Quantifies customer support load driven by platform instability."
        )
    with k6:
        self_svc = kpi_data["self_service_resolution_rate"]["value"]
        k6.metric(
            "Self-Service Resolution",
            f"{self_svc}%",
            help="Percentage of customer tickets resolved via in-app self-service. Why it matters: Reduces support cost and accelerates resolution."
        )
    with k7:
        adopt = kpi_data["adoption_rate"]["value"]
        k7.metric(
            "Sync Feature Adoption",
            f"{adopt}% DAU",
            help="Percentage of active users syncing data. Why it matters: Measures customer engagement with the core sync capability."
        )

st.markdown("---")

# ==============================================================================
# Visualizations: Trends and Failure Breakdown
# ==============================================================================
c_left, c_right = st.columns([1, 1])

# Fetch incidents for visualization
all_incidents = fetch_api("incidents", params={"limit": 50}) or []

with c_left:
    st.subheader("📊 Failure Category Distribution")
    st.caption("Categorization of sync errors across all client ingestion sessions. Identifies primary engineering bottlenecks.")
    
    if all_incidents:
        df_inc = pd.DataFrame(all_incidents)
        cat_counts = df_inc["failure_category"].value_counts().reset_index()
        cat_counts.columns = ["Failure Category", "Incident Count"]
        
        fig_cat = px.bar(
            cat_counts,
            x="Failure Category",
            y="Incident Count",
            color="Failure Category",
            text="Incident Count",
            color_discrete_sequence=px.colors.qualitative.Safe
        )
        fig_cat.update_layout(showlegend=False, height=320, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No failure incident records found.")

with c_right:
    st.subheader("⚡ Incident Severity & Status Distribution")
    st.caption("Distribution of active vs mitigated incidents broken down by severity level.")
    
    if all_incidents:
        fig_pie = px.pie(
            df_inc,
            names="severity",
            title="Incidents by Severity",
            color="severity",
            color_discrete_map={"SEV1": "#ef4444", "SEV2": "#f97316", "SEV3": "#eab308", "SEV4": "#3b82f6"}
        )
        fig_pie.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No incident records available.")

st.markdown("---")

# ==============================================================================
# Open Incidents & Interactive Triage Section
# ==============================================================================
st.subheader("🚨 Incident Directory & Autonomous SRE Triage")
st.caption("Explore incidents, view cohort telemetry, and execute real tool-calling triage investigation.")

filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    status_filter = st.selectbox("Filter Status:", ["ALL", "INVESTIGATING", "DETECTED", "MITIGATED", "RESOLVED"])
with filter_col2:
    sev_filter = st.selectbox("Filter Severity:", ["ALL", "SEV1", "SEV2", "SEV3", "SEV4"])

filtered_incs = all_incidents
if status_filter != "ALL":
    filtered_incs = [i for i in filtered_incs if i["status"] == status_filter]
if sev_filter != "ALL":
    filtered_incs = [i for i in filtered_incs if i["severity"] == sev_filter]

if filtered_incs:
    df_table = pd.DataFrame(filtered_incs)[["id", "title", "severity", "status", "affected_cohort", "failure_category", "start_time"]]
    st.dataframe(df_table, use_container_width=True, hide_index=True)
    
    # Drill-down selector
    incident_options = [i["id"] for i in filtered_incs]
    selected_inc_id = st.selectbox("Select Incident for SRE Investigation:", incident_options)
    
    if selected_inc_id:
        inc_detail = fetch_api(f"incidents/{selected_inc_id}")
        if inc_detail:
            t_col1, t_col2 = st.columns([1, 1])
            with t_col1:
                st.markdown(f"### Details: `{inc_detail['id']}`")
                st.write(f"**Title:** {inc_detail['title']}")
                st.write(f"**Severity:** `{inc_detail['severity']}` | **Status:** `{inc_detail['status']}`")
                st.write(f"**Affected Cohort:** `{inc_detail['affected_cohort']}`")
                st.write(f"**Failure Category:** `{inc_detail['failure_category']}`")
                st.write(f"**Root Cause:** {inc_detail.get('root_cause_summary', 'Pending triage')}")
                
                cohort_telem = inc_detail.get("cohort_telemetry", {})
                if cohort_telem:
                    st.info(f"📊 **Cohort Telemetry:** {cohort_telem.get('failure_events_sampled')} failures out of {cohort_telem.get('total_events_sampled')} sampled events (Avg Latency: {cohort_telem.get('avg_latency_ms')}ms)")
                    
            with t_col2:
                st.markdown("### 🤖 Autonomous Triage Agent")
                st.write("Run structured automated triage using LLM tool-calling or deterministic SRE fallback.")
                
                use_fallback = st.checkbox("Force Deterministic Fallback (Offline Mode)", value=True)
                
                if st.button("🚀 Run SRE Incident Triage", type="primary"):
                    with st.spinner(f"Investigating {selected_inc_id} across database and operational runbooks..."):
                        triage_data = trigger_triage_api(selected_inc_id, force_fallback=use_fallback)
                        
                    if triage_data:
                        st.success(f"Analysis Complete! Mode: `{triage_data['analysis_mode']}` (Confidence: {int(triage_data['confidence']*100)}%)")
                        st.markdown(f"**Executive Summary:** {triage_data['summary']}")
                        st.markdown(f"**Likely Root Cause:** {triage_data['likely_cause']}")
                        st.markdown(f"**Suggested Next Action:** {triage_data['suggested_next_step']}")
                        
                        st.markdown("**Empirical Telemetry Evidence:**")
                        for ev in triage_data.get("evidence", []):
                            st.markdown(f"- {ev}")
                            
                        st.markdown("**Referenced Runbooks:**")
                        for rb in triage_data.get("runbook_references", []):
                            st.markdown(f"- 📖 `{rb}`")
                            
                        st.warning("⚠️ Human-in-the-loop: All automated suggestions are strictly advisory and require SRE operator review.")
else:
    st.info("No incidents match the active filters.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 13px;'>"
    "SyncOps Assistant | Educational SRE Portfolio Project | Independent Demonstration | All Data Synthetic"
    "</div>",
    unsafe_allow_html=True
)
