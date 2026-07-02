import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

BORDER = "#334155"
CARD   = "#1e293b"
BG     = "#0f172a"


def sev_badge(level):
    cfg = {
        "High":   ("#ef4444", "#450a0a"),
        "Medium": ("#f59e0b", "#451a03"),
        "Low":    ("#22c55e", "#052e16"),
    }
    color, bg = cfg.get(level, ("#94a3b8", "#1e293b"))
    return f'<span style="background:{bg};color:{color};border:1px solid {color};border-radius:20px;padding:3px 11px;font-size:12px;font-weight:700">{level}</span>'


def status_badge(status):
    cfg = {
        "Active":       ("#ef4444", "#450a0a"),
        "Acknowledged": ("#f59e0b", "#451a03"),
        "Resolved":     ("#22c55e", "#052e16"),
    }
    color, bg = cfg.get(status, ("#94a3b8", "#1e293b"))
    return f'<span style="background:{bg};color:{color};border:1px solid {color};border-radius:20px;padding:3px 11px;font-size:12px;font-weight:700">{status}</span>'


def show():
    st.markdown("# 🔔 Alerts")
    st.markdown("Fault notifications and system warnings across all production lines.")
    st.markdown("---")

    alerts_all = db.get_alerts()
    machines   = db.get_machines().set_index("machine_id")["machine_name"].to_dict()
    lines      = db.get_production_lines().set_index("line_id")["line_name"].to_dict()

    # ── Filters FIRST (so KPIs reflect filtered data) ─────────────────────────
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
    with f1:
        search = st.text_input("🔍 Search message / machine")
    with f2:
        status_filter = st.selectbox("Status", ["All", "Active", "Acknowledged", "Resolved"])
    with f3:
        severity_filter = st.selectbox("Severity", ["All", "High", "Medium", "Low"])
    with f4:
        line_filter = st.selectbox("Line", ["All"] + [lines[k] for k in sorted(lines)])

    # Apply filters
    df = alerts_all.copy()
    if search:
        mname_series = df["machine_id"].map(lambda x: machines.get(x, ""))
        df = df[df["message"].str.contains(search, case=False) |
                mname_series.str.contains(search, case=False)]
    if status_filter != "All":
        df = df[df["status"] == status_filter]
    if severity_filter != "All":
        df = df[df["level"] == severity_filter]
    if line_filter != "All":
        lid = [k for k, v in lines.items() if v == line_filter][0]
        df  = df[df["line_id"] == lid]

    # ── KPIs — computed from filtered df ─────────────────────────────────────
    st.markdown("---")
    total    = len(df)
    active   = (df["status"] == "Active").sum()
    acked    = (df["status"] == "Acknowledged").sum()
    resolved = (df["status"] == "Resolved").sum()
    critical = (df["level"] == "High").sum()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📋 Filtered Alerts", total)
    k2.metric("🔴 Active",          active,   delta="needs action" if active > 0 else "clear", delta_color="inverse")
    k3.metric("🟡 Acknowledged",    acked)
    k4.metric("🟢 Resolved",        resolved)
    k5.metric("⚠️ High Severity",   critical, delta_color="inverse")
    st.markdown("---")

    st.markdown(f"<div style='color:#94a3b8;font-size:13px;margin-bottom:8px'>Showing <b style='color:#f1f5f9'>{total}</b> alerts</div>",
                unsafe_allow_html=True)

    if df.empty:
        st.info("No alerts match your filter criteria.")
        return

    # ── HTML table ────────────────────────────────────────────────────────────
    rows_html = ""
    for _, row in df.iterrows():
        mname = machines.get(row["machine_id"], f"M-{row['machine_id']}")
        lname = lines.get(row["line_id"],       f"L-{row['line_id']}")
        ts    = str(row["created_at"])[:16]
        rows_html += f"""
        <tr>
            <td>{row['alert_id']}</td>
            <td style="color:#f1f5f9;font-weight:500">{mname}</td>
            <td style="color:#94a3b8">{lname}</td>
            <td style="color:#cbd5e1">{row['message']}</td>
            <td>{sev_badge(row['level'])}</td>
            <td>{status_badge(row['status'])}</td>
            <td style="color:#64748b;white-space:nowrap">{ts}</td>
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
        <th>Message</th><th>Severity</th><th>Status</th><th>Timestamp</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    </body></html>"""

    height = min(600, max(200, len(df) * 48 + 60))
    components.html(html, height=height, scrolling=True)
