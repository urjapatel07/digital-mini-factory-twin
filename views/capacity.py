import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

BORDER = "#334155"
CARD   = "#1e293b"
BG     = "#0f172a"

BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#cbd5e1",
    font_family="Inter",
)
MARG = dict(l=16, r=16, t=44, b=16)
AXIS = dict(gridcolor=BORDER, linecolor=BORDER, zeroline=False)


def utilization_color(pct: float):
    """Returns (text_color, bg_color, label) based on utilization %"""
    if pct < 50:
        return "#3b82f6", "#0c1a3a", "Under-utilized"
    elif pct < 85:
        return "#22c55e", "#052e16", "Optimal"
    elif pct < 95:
        return "#f59e0b", "#451a03", "High Load"
    else:
        return "#ef4444", "#450a0a", "Overloaded"


def gauge_bar(pct: float, width: int = 100) -> str:
    """Returns an HTML progress bar styled by utilization zone."""
    color, _, _ = utilization_color(pct)
    filled = min(pct, 100)
    return (
        f'<div style="background:#0f172a;border-radius:6px;height:8px;width:{width}%;overflow:hidden">'
        f'<div style="background:{color};height:100%;width:{filled:.1f}%;border-radius:6px;'
        f'transition:width 0.3s ease"></div></div>'
    )


def show():
    st.markdown("# ⚙️ Capacity Utilization")
    st.markdown("How hard is each machine being pushed? Spot overloads and wasted capacity at a glance.")
    st.markdown("---")

    # ── Load data ─────────────────────────────────────────────────────────────
    machines = db.get_machines()
    lines    = db.get_production_lines()
    df       = machines.merge(lines, on="line_id")
    df["utilization"] = (df["output"] / df["max_capacity"] * 100).round(1)
    df["zone"]        = df["utilization"].apply(lambda p: utilization_color(p)[2])
    df["zone_color"]  = df["utilization"].apply(lambda p: utilization_color(p)[0])

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2 = st.columns([2, 2])
    with f1:
        line_opts = ["All Lines"] + lines["line_name"].tolist()
        sel_line  = st.selectbox("Production Line", line_opts)
    with f2:
        zone_opts = ["All Zones", "Under-utilized", "Optimal", "High Load", "Overloaded"]
        sel_zone  = st.selectbox("Filter by Zone", zone_opts)

    fdf = df.copy()
    if sel_line != "All Lines":
        fdf = fdf[fdf["line_name"] == sel_line]
    if sel_zone != "All Zones":
        fdf = fdf[fdf["zone"] == sel_zone]

    st.markdown("")

    # ── Zone legend ───────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
        <div style="display:flex;align-items:center;gap:6px">
            <div style="width:12px;height:12px;border-radius:50%;background:#3b82f6"></div>
            <span style="color:#94a3b8;font-size:13px">Under-utilized (&lt;50%)</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
            <div style="width:12px;height:12px;border-radius:50%;background:#22c55e"></div>
            <span style="color:#94a3b8;font-size:13px">Optimal (50–85%)</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
            <div style="width:12px;height:12px;border-radius:50%;background:#f59e0b"></div>
            <span style="color:#94a3b8;font-size:13px">High Load (85–95%)</span>
        </div>
        <div style="display:flex;align-items:center;gap:6px">
            <div style="width:12px;height:12px;border-radius:50%;background:#ef4444"></div>
            <span style="color:#94a3b8;font-size:13px">Overloaded (&gt;95%)</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary KPI cards ─────────────────────────────────────────────────────
    under  = (fdf["zone"] == "Under-utilized").sum()
    optimal= (fdf["zone"] == "Optimal").sum()
    high   = (fdf["zone"] == "High Load").sum()
    over   = (fdf["zone"] == "Overloaded").sum()
    avg_u  = round(fdf["utilization"].mean(), 1) if not fdf.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("📊 Avg Utilization",  f"{avg_u}%")
    k2.metric("🔵 Under-utilized",   under)
    k3.metric("🟢 Optimal",          optimal)
    k4.metric("🟡 High Load",        high)
    k5.metric("🔴 Overloaded",       over)

    st.markdown("---")

    # ── Machine utilization table (HTML via components) ───────────────────────
    st.markdown("#### 🤖 Machine-Level Utilization")

    rows_html = ""
    for _, row in fdf.sort_values("utilization", ascending=False).iterrows():
        color, bg, zone = utilization_color(row["utilization"])
        badge = (f'<span style="background:{bg};color:{color};border:1px solid {color};'
                 f'border-radius:20px;padding:3px 10px;font-size:11px;font-weight:700">{zone}</span>')
        bar   = gauge_bar(row["utilization"], width=100)
        rows_html += f"""
        <tr>
          <td style="padding:11px 14px;color:#f1f5f9;font-weight:500">{row['machine_name']}</td>
          <td style="padding:11px 14px;color:#94a3b8">{row['line_name']}</td>
          <td style="padding:11px 14px;color:#94a3b8">{row['stage']}</td>
          <td style="padding:11px 14px;color:#f1f5f9">{int(row['output'])}</td>
          <td style="padding:11px 14px;color:#64748b">{int(row['max_capacity'])}</td>
          <td style="padding:11px 14px;min-width:160px">
            <div style="display:flex;align-items:center;gap:10px">
              <div style="flex:1">{bar}</div>
              <span style="color:{color};font-weight:700;font-size:13px;white-space:nowrap">{row['utilization']}%</span>
            </div>
          </td>
          <td style="padding:11px 14px">{badge}</td>
        </tr>
        """

    table_html = f"""<!DOCTYPE html><html><head><style>
      *{{box-sizing:border-box;margin:0;padding:0;}}
      body{{background:{BG};font-family:Inter,sans-serif;font-size:13px;color:#cbd5e1;}}
      table{{width:100%;border-collapse:collapse;background:{CARD};border-radius:12px;overflow:hidden;}}
      thead tr{{background:#0f172a;border-bottom:2px solid {BORDER};}}
      th{{padding:11px 14px;text-align:left;color:#64748b;font-size:11px;font-weight:700;
          letter-spacing:.05em;text-transform:uppercase;white-space:nowrap;}}
      td{{border-bottom:1px solid {BORDER};vertical-align:middle;}}
      tbody tr:last-child td{{border-bottom:none;}}
      tbody tr:hover{{background:rgba(255,255,255,0.03);}}
    </style></head><body>
    <table>
      <thead><tr>
        <th>Machine</th><th>Line</th><th>Stage</th>
        <th>Output</th><th>Max Cap.</th><th>Utilization</th><th>Zone</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table></body></html>"""

    height = min(650, max(200, len(fdf) * 50 + 58))
    components.html(table_html, height=height, scrolling=True)

    st.markdown("")

    # ── Charts row ────────────────────────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.markdown("#### 📊 Utilization by Machine")
        chart_df = fdf.sort_values("utilization", ascending=True)
        fig = go.Figure(go.Bar(
            x=chart_df["utilization"],
            y=chart_df["machine_name"],
            orientation="h",
            marker_color=chart_df["zone_color"].tolist(),
            text=[f"{v}%" for v in chart_df["utilization"]],
            textposition="outside",
            textfont_color="#f1f5f9",
        ))
        # Zone boundary lines
        for xval, label, color in [(50, "50%", "#3b82f6"), (85, "85%", "#f59e0b"), (95, "95%", "#ef4444")]:
            fig.add_vline(x=xval, line_dash="dash", line_color=color, opacity=0.5,
                          annotation_text=label, annotation_font_color=color,
                          annotation_position="top")
        fig.update_layout(
            **BASE, margin=MARG,
            xaxis=dict(range=[0, 115], gridcolor=BORDER, linecolor=BORDER,
                       zeroline=False, title="Utilization (%)"),
            yaxis=AXIS,
            height=max(300, len(fdf) * 32 + 60),
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### 🍩 Zone Distribution")
        zone_counts = fdf.groupby("zone").size().reset_index(name="count")
        zone_color_map = {
            "Under-utilized": "#3b82f6",
            "Optimal":        "#22c55e",
            "High Load":      "#f59e0b",
            "Overloaded":     "#ef4444",
        }
        zone_counts["color"] = zone_counts["zone"].map(zone_color_map)

        fig2 = go.Figure(go.Pie(
            labels=zone_counts["zone"],
            values=zone_counts["count"],
            hole=0.55,
            marker_colors=zone_counts["color"].tolist(),
            textinfo="label+percent",
            textfont_size=12,
        ))
        fig2.update_layout(
            **BASE,
            margin=dict(l=8, r=8, t=44, b=8),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── Line-level rollup ─────────────────────────────────────────────────────
    st.markdown("#### 🏭 Line-Level Capacity Rollup")

    line_df = fdf.groupby("line_name").agg(
        total_output   =("output", "sum"),
        total_capacity =("max_capacity", "sum"),
    ).reset_index()
    line_df["utilization"] = (line_df["total_output"] / line_df["total_capacity"] * 100).round(1)
    line_df["zone"]        = line_df["utilization"].apply(lambda p: utilization_color(p)[2])
    line_df["color"]       = line_df["utilization"].apply(lambda p: utilization_color(p)[0])

    cols = st.columns(len(line_df))
    for col, (_, row) in zip(cols, line_df.iterrows()):
        color, bg, zone = utilization_color(row["utilization"])
        col.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORDER};border-left:4px solid {color};
                    border-radius:12px;padding:18px 20px">
            <div style="font-size:13px;color:#94a3b8;margin-bottom:4px">{row['line_name']}</div>
            <div style="font-size:28px;font-weight:700;color:{color};margin-bottom:6px">{row['utilization']}%</div>
            <div style="margin-bottom:10px">{gauge_bar(row['utilization'], width=100)}</div>
            <span style="background:{bg};color:{color};border:1px solid {color};
                   border-radius:20px;padding:2px 10px;font-size:11px;font-weight:700">{zone}</span>
            <div style="margin-top:12px;border-top:1px solid {BORDER};padding-top:10px;
                        display:flex;gap:20px">
                <div>
                    <div style="font-size:11px;color:#64748b">Output</div>
                    <div style="font-weight:600;color:#f1f5f9">{int(row['total_output']):,}</div>
                </div>
                <div>
                    <div style="font-size:11px;color:#64748b">Capacity</div>
                    <div style="font-weight:600;color:#f1f5f9">{int(row['total_capacity']):,}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # ── Scatter: Utilization vs Efficiency ────────────────────────────────────
    st.markdown("#### 🔬 Utilization vs Efficiency")
    st.markdown("<div style='color:#94a3b8;font-size:13px;margin-bottom:12px'>Does running a machine harder hurt its efficiency? Each dot is one machine.</div>",
                unsafe_allow_html=True)

    fig3 = px.scatter(
        fdf, x="utilization", y="efficiency",
        color="line_name",
        hover_name="machine_name",
        hover_data={"utilization": True, "efficiency": True, "line_name": False},
        labels={"utilization": "Utilization (%)", "efficiency": "Efficiency (%)"},
        color_discrete_sequence=["#3b82f6", "#22c55e", "#f59e0b", "#a855f7"],
    )
    for xval, color in [(50, "#3b82f6"), (85, "#f59e0b"), (95, "#ef4444")]:
        fig3.add_vline(x=xval, line_dash="dot", line_color=color, opacity=0.4)
    fig3.update_traces(marker_size=10, marker_line_width=1, marker_line_color="#0f172a")
    fig3.update_layout(
        **BASE, margin=MARG,
        xaxis=dict(title="Utilization (%)", gridcolor=BORDER, linecolor=BORDER, zeroline=False),
        yaxis=dict(title="Efficiency (%)",  gridcolor=BORDER, linecolor=BORDER, zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", title_text="Line"),
        height=380,
    )
    st.plotly_chart(fig3, use_container_width=True)
