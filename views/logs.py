import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

BORDER = "#334155"
CARD   = "#1e293b"
BG     = "#0f172a"


def event_color(action: str):
    a = action.lower()
    if "fault" in a or "fail" in a or "error" in a:
        return "#ef4444", "#450a0a"
    if "delay" in a or "rework" in a or "stop" in a:
        return "#f59e0b", "#451a03"
    if "done" in a or "complete" in a or "pass" in a or "start" in a:
        return "#22c55e", "#052e16"
    return "#94a3b8", "#1e293b"


def infer_event_type(action: str):
    a = action.lower()
    if "fault" in a or "fail" in a or "error" in a:
        return "Failure"
    if "delay" in a or "rework" in a:
        return "Delay"
    if "done" in a or "complete" in a:
        return "Success"
    return "Info"


def show():
    st.markdown("# 📋 Logs")
    st.markdown("Historical activity records for all machines and production events.")
    st.markdown("---")

    logs_raw = db.get_logs()
    logs_raw["event_type"] = logs_raw["action"].apply(infer_event_type)
    logs_raw["timestamp"]  = pd.to_datetime(logs_raw["timestamp"])

    lines = db.get_production_lines()

    # ── Filters FIRST ─────────────────────────────────────────────────────────
    f1, f2, f3, f4 = st.columns([3, 2, 2, 2])
    with f1:
        kw = st.text_input("🔍 Search action / machine")
    with f2:
        evt_filter = st.selectbox("Event Type", ["All", "Failure", "Delay", "Success", "Info"])
    with f3:
        line_opts = ["All Lines"] + lines["line_name"].tolist()
        sel_line  = st.selectbox("Production Line", line_opts)
    with f4:
        sort_order = st.selectbox("Sort", ["Newest First", "Oldest First"])

    # Apply filters
    df = logs_raw.copy()
    if kw:
        df = df[df["action"].str.contains(kw, case=False) |
                df["machine_name"].fillna("").str.contains(kw, case=False)]
    if evt_filter != "All":
        df = df[df["event_type"] == evt_filter]
    if sel_line != "All Lines":
        lid = int(lines[lines["line_name"] == sel_line]["line_id"].iloc[0])
        df  = df[df["line_id"] == lid]
    df = df.sort_values("timestamp", ascending=(sort_order == "Oldest First"))

    # ── KPIs — computed from filtered df ─────────────────────────────────────
    st.markdown("---")
    total           = len(df)
    failures        = (df["event_type"] == "Failure").sum()
    delays          = (df["event_type"] == "Delay").sum()
    machines_active = df["machine_id"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("📄 Filtered Logs",      total)
    k2.metric("❌ Failure Events",     failures)
    k3.metric("⏳ Delay Events",       delays)
    k4.metric("🤖 Machines in View",   machines_active)
    st.markdown("---")

    st.markdown(f"<div style='color:#94a3b8;font-size:13px;margin-bottom:8px'>Showing <b style='color:#f1f5f9'>{total}</b> log entries</div>",
                unsafe_allow_html=True)

    if df.empty:
        st.info("No log entries match your filters.")
        return

    # Paginate
    page_size   = 50
    total_pages = max(1, (len(df) - 1) // page_size + 1)
    page_num    = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)
    page_df     = df.iloc[(page_num - 1) * page_size : page_num * page_size]

    # ── HTML table ────────────────────────────────────────────────────────────
    rows_html = ""
    for _, row in page_df.iterrows():
        color, bg = event_color(row["action"])
        mname  = row.get("machine_name") or f"Machine {row['machine_id']}"
        lname  = row.get("line_name")    or f"Line {row['line_id']}"
        ts_str = str(row["timestamp"])[:19]
        badge  = f'<span style="background:{bg};color:{color};border:1px solid {color};border-radius:20px;padding:3px 10px;font-size:11px;font-weight:700">{row["event_type"]}</span>'
        rows_html += f"""
        <tr>
            <td style="color:#64748b">{row['log_id']}</td>
            <td style="color:#f1f5f9;font-weight:500">{mname}</td>
            <td style="color:#94a3b8">{lname}</td>
            <td>{badge}</td>
            <td style="color:#cbd5e1">{row['action']}</td>
            <td style="color:#64748b;white-space:nowrap">{ts_str}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html><html><head><style>
      * {{ box-sizing:border-box; margin:0; padding:0; }}
      body {{ background:{BG}; font-family:Inter,sans-serif; font-size:13px; color:#cbd5e1; }}
      table {{ width:100%; border-collapse:collapse; background:{CARD}; border-radius:12px; overflow:hidden; }}
      thead tr {{ background:#0f172a; border-bottom:2px solid {BORDER}; }}
      th {{ padding:12px 14px; text-align:left; color:#64748b; font-size:11px; font-weight:700;
            letter-spacing:0.05em; text-transform:uppercase; white-space:nowrap; }}
      td {{ padding:11px 14px; border-bottom:1px solid {BORDER}; vertical-align:middle; }}
      tbody tr:last-child td {{ border-bottom:none; }}
      tbody tr:hover {{ background:rgba(255,255,255,0.03); }}
    </style></head><body>
    <table>
      <thead><tr>
        <th>ID</th><th>Machine</th><th>Line</th>
        <th>Type</th><th>Action</th><th>Timestamp</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    </body></html>"""

    height = min(700, max(200, len(page_df) * 48 + 60))
    components.html(html, height=height, scrolling=True)

    st.markdown(f"<div style='color:#64748b;font-size:12px;margin-top:8px;text-align:right'>Page {page_num} of {total_pages} · {total} total entries</div>",
                unsafe_allow_html=True)
