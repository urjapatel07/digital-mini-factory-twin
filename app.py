import streamlit as st

st.set_page_config(
    page_title="Digital Twin Factory",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 14px; padding: 5px 0; }

/* Section labels in sidebar */
.sidebar-section {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #475569;
    padding: 14px 0 4px 0;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
}
[data-testid="metric-container"] label {
    color: #94a3b8 !important; font-size: 13px !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important; font-size: 28px !important; font-weight: 700 !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] { font-size: 13px !important; }

/* Page background */
.main .block-container { background: #0f172a; padding-top: 24px; }
.stApp { background: #0f172a; }

/* Headers */
h1, h2, h3 { color: #f1f5f9 !important; }
p, li, span { color: #cbd5e1; }

/* Divider */
hr { border-color: #334155; }

/* Buttons */
.stButton>button {
    background: #3b82f6; color: white; border: none;
    border-radius: 8px; font-weight: 600; padding: 8px 20px;
}
.stButton>button:hover { background: #2563eb; }

/* Selectbox / inputs */
.stSelectbox>div>div, .stTextInput>div>div {
    background: #1e293b !important; color: #f1f5f9 !important;
    border-color: #334155 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏭 Digital Twin")
    st.markdown("---")

    ALL_PAGES = [
        "📊 Dashboard",
        "📈 Analytics",
        "🔔 Alerts",
        "📋 Logs",
        "⚙️ Simulation",
        "📦 Capacity Utilization",
    ]

    if "page" not in st.session_state or st.session_state.page not in ALL_PAGES:
        st.session_state.page = "📊 Dashboard"

    selected = st.radio(
        "Navigation",
        ALL_PAGES,
        index=ALL_PAGES.index(st.session_state.page),
        label_visibility="collapsed",
        key="nav_radio",
    )
    st.session_state.page = selected

    st.markdown("---")
    st.markdown("<small style='color:#475569'>DE II-B · 2025-26</small>", unsafe_allow_html=True)


# ── Routing ───────────────────────
page = st.session_state.page

if page == "📊 Dashboard":
    from views.dashboard import show
elif page == "📈 Analytics":
    from views.analytics import show
elif page == "🔔 Alerts":
    from views.alerts import show
elif page == "📋 Logs":
    from views.logs import show
elif page == "⚙️ Simulation":
    from views.simulation import show
elif page == "📦 Capacity Utilization":
    from views.capacity import show
else:
    st.error(f"Unknown page: {page}")

show()