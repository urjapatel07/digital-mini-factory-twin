import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

BORDER = "#334155"
CARD   = "#1e293b"
COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#a855f7", "#ec4899", "#14b8a6"]

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Inter",
)
MARG = dict(l=16, r=16, t=44, b=16)
AXIS = dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False)


def show():
    st.markdown("# 📈 Analytics")
    st.markdown("Deep-dive into production performance and machine health.")
    st.markdown("---")

    lines      = db.get_production_lines()
    line_names = ["All Lines"] + lines["line_name"].tolist()

    sel_line = st.selectbox("Production Line", line_names)

    st.markdown("")

    lid = None if sel_line == "All Lines" else int(lines[lines["line_name"] == sel_line]["line_id"].iloc[0])

    prod = db.get_production_data()
    prod["timestamp"] = pd.to_datetime(prod["timestamp"])
    if lid:
        prod = prod[prod["line_id"] == lid]

    # Always load ALL metrics for the defect chart, filter only for others
    metrics_all = db.get_metrics()
    metrics_all["timestamp"] = pd.to_datetime(metrics_all["timestamp"])

    metrics = metrics_all.copy()
    if lid:
        metrics = metrics[metrics["line_id"] == lid]

    machines = db.get_machines(lid)

    # ── Row 1: Production trend + Defect distribution ─────────────────────────
    r1l, r1r = st.columns([3, 2])

    with r1l:
        st.markdown("#### 📊 Production Trend Over Time")
        agg = prod.groupby([prod["timestamp"].dt.date, "line_name"])["units_produced"].sum().reset_index()
        agg.columns = ["Date", "Line", "Units"]
        fig = px.area(agg, x="Date", y="Units", color="Line", color_discrete_sequence=COLORS)
        fig.update_layout(**BASE, margin=MARG, xaxis=AXIS, yaxis=AXIS,
                          legend=dict(bgcolor="rgba(0,0,0,0)"))
        fig.update_traces(line_width=1.5, opacity=0.85)
        st.plotly_chart(fig, use_container_width=True)

    with r1r:
        st.markdown("#### 🔍 Defect Rate by Line")
        # Always compare across all lines — show selected line highlighted if filtered
        def_df = metrics_all.groupby("line_name")["defect_rate"].mean().reset_index()
        def_df.columns = ["Line", "Avg Defect Rate (%)"]
        def_df = def_df.sort_values("Avg Defect Rate (%)", ascending=True)

        # Highlight selected line, grey out others
        if lid:
            sel_name = lines[lines["line_id"] == lid]["line_name"].iloc[0]
            bar_colors = [COLORS[0] if l == sel_name else "#334155" for l in def_df["Line"]]
        else:
            bar_colors = COLORS[:len(def_df)]

        fig2 = go.Figure(go.Bar(
            x=def_df["Avg Defect Rate (%)"],
            y=def_df["Line"],
            orientation="h",
            marker_color=bar_colors,
            text=[f"{v:.2f}%" for v in def_df["Avg Defect Rate (%)"]],
            textposition="outside",
            textfont_color="#f1f5f9",
        ))
        fig2.update_layout(
            **BASE, margin=MARG,
            xaxis=dict(title="Avg Defect Rate (%)", gridcolor=BORDER, linecolor=BORDER, zeroline=False),
            yaxis=AXIS,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Row 2: Heatmap + Cycle time ───────────────────────────────────────────
    r2l, r2r = st.columns(2)

    with r2l:
        st.markdown("#### 🌡️ Machine Utilization Heatmap")
        mach_all = db.get_machines().merge(db.get_production_lines(), on="line_id")
        if lid:
            mach_all = mach_all[mach_all["line_id"] == lid]
        pivot = mach_all.pivot_table(
            index="line_name", columns="stage",
            values="efficiency", aggfunc="mean"
        ).fillna(0)
        fig3 = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="Blues",
            text=np.round(pivot.values, 1),
            texttemplate="%{text}%",
            hovertemplate="Stage: %{x}<br>Line: %{y}<br>Efficiency: %{z:.1f}%<extra></extra>",
            colorbar=dict(tickfont=dict(color="#cbd5e1"),
                          title=dict(text="Efficiency %", font=dict(color="#cbd5e1"))),
        ))
        fig3.update_layout(**BASE, margin=MARG,
                           xaxis=dict(tickangle=-30, tickfont_size=11, gridcolor=BORDER),
                           yaxis=AXIS)
        st.plotly_chart(fig3, use_container_width=True)

    with r2r:
        st.markdown("#### ⏱️ Avg Cycle Time per Machine")
        machines_all = db.get_machines().merge(db.get_production_lines(), on="line_id")
        if lid:
            machines_all = machines_all[machines_all["line_id"] == lid]
        machines_all = machines_all[machines_all["output"] > 0].copy()
        machines_all["cycle_time"] = (machines_all["runtime"] / machines_all["output"]).round(2)
        top = machines_all.nlargest(10, "cycle_time")
        fig4 = go.Figure(go.Bar(
            y=top["machine_name"], x=top["cycle_time"],
            orientation="h",
            marker_color="#3b82f6",
            text=[f"{v:.2f}" for v in top["cycle_time"]],
            textposition="outside",
            textfont_color="#f1f5f9",
        ))
        fig4.update_layout(**BASE, margin=MARG,
                           xaxis=dict(title="Mins/Unit", gridcolor=BORDER, linecolor=BORDER, zeroline=False),
                           yaxis=AXIS)
        st.plotly_chart(fig4, use_container_width=True)

    # ── Row 3: Throughput ──────────────────────────────────────────────────────
    st.markdown("#### 🚀 Throughput Over Time")
    tp = metrics.groupby([metrics["timestamp"].dt.date, "line_name"])["throughput"].mean().reset_index()
    tp.columns = ["Date", "Line", "Throughput"]
    fig5 = px.line(tp, x="Date", y="Throughput", color="Line",
                   color_discrete_sequence=COLORS, markers=True)
    fig5.update_layout(**BASE, margin=MARG, xaxis=AXIS,
                       yaxis=dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False, title="Throughput (units/hr)"),
                       legend=dict(bgcolor="rgba(0,0,0,0)"), height=300)
    fig5.update_traces(marker_size=4)
    st.plotly_chart(fig5, use_container_width=True)

    # ── Insight cards ──────────────────────────────────────────────────────────
    st.markdown("#### 💡 Key Insights")
    i1, i2, i3 = st.columns(3)

    low_eff  = machines[machines["efficiency"] < 80] if not machines.empty else pd.DataFrame()
    avg_def  = metrics["defect_rate"].mean()          if not metrics.empty  else 0
    high_out = machines.nlargest(1, "output")         if not machines.empty else pd.DataFrame()

    with i1:
        st.markdown(f"""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px">
            <div style="color:#f59e0b;font-weight:700;margin-bottom:6px">⚠️ Low Efficiency</div>
            <div style="color:#f1f5f9;font-size:22px;font-weight:700">{len(low_eff)}</div>
            <div style="color:#94a3b8;font-size:13px">machines below 80% efficiency</div>
        </div>""", unsafe_allow_html=True)

    with i2:
        st.markdown(f"""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px">
            <div style="color:#ef4444;font-weight:700;margin-bottom:6px">🔴 Avg Defect Rate</div>
            <div style="color:#f1f5f9;font-size:22px;font-weight:700">{avg_def:.2f}%</div>
            <div style="color:#94a3b8;font-size:13px">{'for ' + sel_line if lid else 'across all lines'}</div>
        </div>""", unsafe_allow_html=True)

    with i3:
        top_m = high_out.iloc[0]["machine_name"] if not high_out.empty else "—"
        top_o = int(high_out.iloc[0]["output"])   if not high_out.empty else 0
        st.markdown(f"""
        <div style="background:#1e293b;border:1px solid #334155;border-radius:12px;padding:16px">
            <div style="color:#22c55e;font-weight:700;margin-bottom:6px">🏆 Top Machine</div>
            <div style="color:#f1f5f9;font-size:18px;font-weight:700">{top_m}</div>
            <div style="color:#94a3b8;font-size:13px">{top_o:,} units produced</div>
        </div>""", unsafe_allow_html=True)
