import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

CARD   = "#1e293b"
BORDER = "#334155"

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Inter",
)
MARG = dict(l=16, r=16, t=40, b=16)
AXIS = dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False)


def show():
    st.markdown("# 📊 Dashboard")
    st.markdown("Real-time factory overview · refreshes on each interaction")
    st.markdown("---")

    kpis = db.get_summary_kpis()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏭 Total Output",   f"{kpis['total_output']:,} units")
    c2.metric("⚡ Active Lines",    f"{kpis['active_lines']} / 4")
    c3.metric("🔔 Active Alerts",   kpis["active_alerts"],
              delta="requires attention" if kpis["active_alerts"] > 5 else "nominal",
              delta_color="inverse")
    c4.metric("⚙️ Avg Efficiency",  f"{kpis['avg_efficiency']}%")

    st.markdown("")
    st.markdown("### 🔌 Production Line Status")
    lines    = db.get_production_lines()
    machines = db.get_machines()

    cols = st.columns(len(lines))
    for col, (_, line) in zip(cols, lines.iterrows()):
        lm      = machines[machines["line_id"] == line["line_id"]]
        running = (lm["status"] == "Running").sum()
        idle    = (lm["status"] == "Idle").sum()
        fault   = lm["status"].isin(["Fault", "Stopped"]).sum()
        out     = lm["output"].sum()
        eff     = round(lm["efficiency"].mean(), 1)

        if fault > 0:
            badge_color, badge_text, badge_bg = "#ef4444", "FAULT", "#450a0a"
        elif running == len(lm):
            badge_color, badge_text, badge_bg = "#22c55e", "ALL RUNNING", "#052e16"
        else:
            badge_color, badge_text, badge_bg = "#f59e0b", "MIXED", "#451a03"

        col.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORDER};border-radius:14px;padding:18px 20px;">
            <div style="font-size:13px;color:#94a3b8;margin-bottom:4px">{line['product_name']}</div>
            <div style="font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:10px">{line['line_name']}</div>
            <span style="background:{badge_bg};color:{badge_color};border:1px solid {badge_color};
                   border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700">{badge_text}</span>
            <div style="margin-top:14px;display:flex;gap:16px;flex-wrap:wrap">
                <div><div style="font-size:11px;color:#64748b">Running</div><div style="font-weight:600;color:#22c55e">{running}</div></div>
                <div><div style="font-size:11px;color:#64748b">Idle</div><div style="font-weight:600;color:#f59e0b">{idle}</div></div>
                <div><div style="font-size:11px;color:#64748b">Fault</div><div style="font-weight:600;color:#ef4444">{fault}</div></div>
            </div>
            <div style="margin-top:12px;border-top:1px solid {BORDER};padding-top:10px;display:flex;gap:20px">
                <div><div style="font-size:11px;color:#64748b">Output</div><div style="font-weight:600;color:#f1f5f9">{out:,}</div></div>
                <div><div style="font-size:11px;color:#64748b">Efficiency</div><div style="font-weight:600;color:#f1f5f9">{eff}%</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    left, right = st.columns([3, 2])

    with left:
        st.markdown("### 📈 Production Trend")
        prod = db.get_production_data()
        prod["timestamp"] = pd.to_datetime(prod["timestamp"])
        prod_agg = prod.groupby(["line_name", prod["timestamp"].dt.date])["units_produced"].sum().reset_index()
        prod_agg.columns = ["Line", "Date", "Units Produced"]
        prod_agg = prod_agg.sort_values("Date")
        fig = px.line(prod_agg, x="Date", y="Units Produced", color="Line",
                      color_discrete_sequence=["#3b82f6", "#22c55e", "#f59e0b", "#a855f7"])
        fig.update_layout(**BASE, margin=MARG, xaxis=AXIS, yaxis=AXIS,
                          legend=dict(bgcolor="rgba(0,0,0,0)"))
        fig.update_traces(line_width=2)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("### ⚙️ Machine Efficiency by Line")
        eff_avg = machines.merge(db.get_production_lines(), on="line_id")[["line_name", "efficiency"]]
        eff_avg = eff_avg.groupby("line_name")["efficiency"].mean().reset_index()
        eff_avg.columns = ["Line", "Efficiency"]
        fig2 = go.Figure(go.Bar(
            x=eff_avg["Efficiency"], y=eff_avg["Line"],
            orientation="h",
            marker_color=["#3b82f6", "#22c55e", "#f59e0b", "#a855f7"],
            text=[f"{v:.1f}%" for v in eff_avg["Efficiency"]],
            textposition="outside",
            textfont_color="#f1f5f9",
        ))
        fig2.update_layout(**BASE, margin=MARG,
                           xaxis=dict(range=[0, 110], gridcolor=BORDER, linecolor=BORDER, zeroline=False),
                           yaxis=AXIS)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 🔔 Recent Active Alerts")
    alerts = db.get_alerts("Active").head(8)
    if alerts.empty:
        st.success("No active alerts — all systems nominal.")
    else:
        lines_map    = db.get_production_lines().set_index("line_id")["line_name"].to_dict()
        machines_map = db.get_machines().set_index("machine_id")["machine_name"].to_dict()
        for _, row in alerts.iterrows():
            sev   = row["level"]
            color = "#ef4444" if sev == "High" else "#f59e0b" if sev == "Medium" else "#22c55e"
            bg    = "#450a0a" if sev == "High" else "#451a03" if sev == "Medium" else "#052e16"
            mname = machines_map.get(row["machine_id"], f"Machine {row['machine_id']}")
            lname = lines_map.get(row["line_id"], f"Line {row['line_id']}")
            st.markdown(f"""
            <div style="background:{bg};border-left:4px solid {color};border-radius:8px;
                        padding:10px 16px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
                <div>
                    <span style="color:{color};font-weight:700;font-size:13px">[{sev}]</span>
                    <span style="color:#f1f5f9;margin-left:8px">{row['message']}</span>
                    <span style="color:#64748b;font-size:12px;margin-left:12px">— {mname} · {lname}</span>
                </div>
                <div style="color:#64748b;font-size:12px;white-space:nowrap">{str(row['created_at'])[:16]}</div>
            </div>
            """, unsafe_allow_html=True)
