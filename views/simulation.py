import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db

BORDER = "#334155"
CARD   = "#1e293b"


def machine_card(machine, sim_state):
    mid   = machine["machine_id"]
    name  = machine["machine_name"]
    stage = machine["stage"]
    seq   = machine["sequence_order"]

    state = sim_state.get(mid, {})
    status   = state.get("status", machine["status"])
    output   = state.get("output", machine["output"])
    queue    = state.get("queue", random.randint(0, 15))
    eff      = state.get("efficiency", machine["efficiency"])

    color_map = {
        "Running": ("#22c55e", "#052e16"),
        "Idle":    ("#f59e0b", "#451a03"),
        "Fault":   ("#ef4444", "#450a0a"),
        "Stopped": ("#ef4444", "#450a0a"),
    }
    color, bg = color_map.get(status, ("#94a3b8", "#1e293b"))

    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-left:4px solid {color};
                border-radius:12px;padding:14px 16px;position:relative">
        <div style="font-size:11px;color:#64748b;margin-bottom:2px">#{seq} · {stage}</div>
        <div style="font-weight:700;color:#f1f5f9;font-size:14px;margin-bottom:8px">{name}</div>
        <span style="background:{bg};color:{color};border:1px solid {color};
               border-radius:20px;padding:2px 8px;font-size:11px;font-weight:700">{status}</span>
        <div style="margin-top:10px;display:grid;grid-template-columns:1fr 1fr;gap:6px">
            <div style="background:#0f172a;border-radius:8px;padding:6px 10px">
                <div style="font-size:10px;color:#64748b">Output</div>
                <div style="font-weight:700;color:#f1f5f9">{output}</div>
            </div>
            <div style="background:#0f172a;border-radius:8px;padding:6px 10px">
                <div style="font-size:10px;color:#64748b">Queue</div>
                <div style="font-weight:700;color:#f59e0b">{queue}</div>
            </div>
            <div style="background:#0f172a;border-radius:8px;padding:6px 10px;grid-column:span 2">
                <div style="font-size:10px;color:#64748b">Efficiency</div>
                <div style="font-weight:700;color:#3b82f6">{eff:.1f}%</div>
            </div>
        </div>
    </div>
    """


def render_machine_grid(machines, sim_state):
    """Renders machine cards in rows of 4 with arrows between rows."""
    cols_per_row = 4
    mach_chunks  = [machines[i:i+cols_per_row] for i in range(0, len(machines), cols_per_row)]
    last_idx     = len(mach_chunks) - 1

    for i, chunk in enumerate(mach_chunks):
        cols = st.columns(len(chunk))
        for col, m in zip(cols, chunk):
            col.markdown(machine_card(m, sim_state), unsafe_allow_html=True)
        # Show arrow after every row except the last
        if i < last_idx:
            st.markdown(
                "<div style='text-align:center;color:#334155;font-size:24px;margin:4px 0'>↓</div>",
                unsafe_allow_html=True
            )


def show():
    st.markdown("# ⚙️ Simulation")
    st.markdown("Interactive factory simulation — Live and Replay modes.")
    st.markdown("---")

    lines = db.get_production_lines()

    # ── Mode selector ─────────────────────────────────────────────────────────
    mode_col, line_col = st.columns([2, 3])
    with mode_col:
        mode = st.radio("Simulation Mode", ["⚡ Live Mode", "🔁 Replay Mode"], horizontal=True)
    with line_col:
        sel_line = st.selectbox("Production Line", lines["line_name"].tolist())

    lid      = int(lines[lines["line_name"] == sel_line]["line_id"].iloc[0])
    machines = db.get_machines(lid).sort_values("sequence_order").to_dict("records")

    st.markdown("")

    # ════════════════════════════════════════════════════════════════════════
    if "⚡ Live" in mode:
        # ── Live Mode ─────────────────────────────────────────────────────
        st.markdown("### ⚡ Live Mode")

        ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
        start = ctrl1.button("▶ Start Simulation")
        pause = ctrl2.button("⏸ Pause")
        reset = ctrl3.button("↺ Reset")
        speed = ctrl4.slider("Speed", 0.5, 3.0, 1.0, 0.5, format="%.1fx")

        if "sim_running" not in st.session_state: st.session_state.sim_running = False
        if "sim_state"   not in st.session_state: st.session_state.sim_state   = {}
        if "sim_tick"    not in st.session_state: st.session_state.sim_tick    = 0
        if "sim_alerts"  not in st.session_state: st.session_state.sim_alerts  = []
        if "sim_out"     not in st.session_state: st.session_state.sim_out     = 0
        if "sim_defects" not in st.session_state: st.session_state.sim_defects = 0
        if "sim_faults"  not in st.session_state: st.session_state.sim_faults  = 0

        if reset:
            st.session_state.sim_running = False
            st.session_state.sim_state   = {}
            st.session_state.sim_tick    = 0
            st.session_state.sim_alerts  = []
            st.session_state.sim_out     = 0
            st.session_state.sim_defects = 0
            st.session_state.sim_faults  = 0
        if start: st.session_state.sim_running = True
        if pause: st.session_state.sim_running = False

        if st.session_state.sim_running:
            st.session_state.sim_tick += 1
            new_alerts = []

            for m in machines:
                mid  = m["machine_id"]
                prev = st.session_state.sim_state.get(mid, {
                    "status": m["status"], "output": m["output"],
                    "queue": 0, "efficiency": m["efficiency"]
                })

                roll = random.random()
                if roll < 0.05:
                    new_status = "Fault"
                    new_eff    = max(0, prev["efficiency"] - random.uniform(5, 20))
                    new_alerts.append({"machine": m["machine_name"], "msg": f"Fault detected at {m['machine_name']}!", "level": "High"})
                    st.session_state.sim_faults += 1
                elif roll < 0.12:
                    new_status = "Idle"
                    new_eff    = prev["efficiency"]
                elif prev["status"] == "Fault" and roll > 0.7:
                    new_status = "Running"
                    new_eff    = min(100, prev["efficiency"] + random.uniform(5, 15))
                else:
                    new_status = "Running"
                    new_eff    = min(100, prev["efficiency"] + random.uniform(-2, 3))

                delta_out  = random.randint(1, 10) if new_status == "Running" else 0
                delta_def  = random.randint(0, 2)  if new_status == "Running" else 0
                new_output = prev["output"] + delta_out
                new_queue  = max(0, prev["queue"] + random.randint(-3, 5))

                st.session_state.sim_out     += delta_out
                st.session_state.sim_defects += delta_def
                st.session_state.sim_state[mid] = {
                    "status": new_status, "output": new_output,
                    "queue":  new_queue,  "efficiency": round(new_eff, 1)
                }

            st.session_state.sim_alerts = (new_alerts + st.session_state.sim_alerts)[:5]

        if st.session_state.sim_alerts:
            for a in st.session_state.sim_alerts:
                st.markdown(f"""
                <div style="background:#450a0a;border-left:4px solid #ef4444;border-radius:8px;
                            padding:10px 16px;margin-bottom:6px">
                    <span style="color:#ef4444;font-weight:700">🚨 [{a['level']}]</span>
                    <span style="color:#f1f5f9;margin-left:8px">{a['msg']}</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("#### 🏭 Production Flow")
        render_machine_grid(machines, st.session_state.sim_state)

        st.markdown("")
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📦 Simulated Output", st.session_state.sim_out)
        m2.metric("🔴 Defects",          st.session_state.sim_defects)
        m3.metric("⚡ Fault Events",      st.session_state.sim_faults)
        m4.metric("🔄 Simulation Ticks", st.session_state.sim_tick)

        if st.session_state.sim_running:
            time.sleep(1 / speed)
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    else:
        # ── Replay Mode ───────────────────────────────────────────────────
        st.markdown("### 🔁 Replay Mode")
        st.markdown("Browse historical machine events by date and time.")

        logs = db.get_logs(lid)
        logs["timestamp"] = pd.to_datetime(logs["timestamp"])
        dates = sorted(logs["timestamp"].dt.date.unique())

        if not dates:
            st.warning("No logs found for this production line.")
            return

        r1, r2 = st.columns(2)
        with r1:
            sel_date = st.selectbox("Select Date", dates, index=len(dates)-1,
                                    format_func=lambda d: str(d))
        day_logs = logs[logs["timestamp"].dt.date == sel_date].sort_values("timestamp")

        if day_logs.empty:
            st.info("No activity recorded on this date.")
            return

        with r2:
            ts_opts = day_logs["timestamp"].dt.strftime("%H:%M:%S").tolist()
            sel_ts  = st.selectbox("Select Time Snapshot", ts_opts, index=len(ts_opts)-1)

        sel_full = pd.to_datetime(f"{sel_date} {sel_ts}")
        snap     = day_logs[day_logs["timestamp"] <= sel_full]

        st.markdown(f"#### 🏭 Machine State at `{sel_date} {sel_ts}`")

        # Build machine states from logs up to snapshot
        replay_state = {}
        for m in machines:
            mid    = m["machine_id"]
            m_logs = snap[snap["machine_id"] == mid]
            if not m_logs.empty:
                last_action = m_logs.iloc[-1]["action"].lower()
                if "fault" in last_action or "error" in last_action:
                    status = "Fault"
                elif "done" in last_action or "complete" in last_action:
                    status = "Running"
                elif "delay" in last_action:
                    status = "Idle"
                else:
                    status = m["status"]
                replay_state[mid] = {
                    "status":     status,
                    "output":     m["output"],
                    "queue":      len(m_logs) % 10,
                    "efficiency": m["efficiency"],
                }
        
        render_machine_grid(machines, replay_state)

        # ── Event Timeline ─────────────────────────────────────────────────
        st.markdown("")
        st.markdown("#### 📅 Event Timeline")

        if snap.empty:
            st.info("No events recorded up to this timestamp.")
            return

        rows_html = ""
        for _, row in snap.iterrows():
            action = row["action"]
            a      = action.lower()
            if "fault" in a or "error" in a:
                color = "#ef4444"
            elif "delay" in a or "rework" in a:
                color = "#f59e0b"
            elif "done" in a or "complete" in a or "passed" in a:
                color = "#22c55e"
            else:
                color = "#94a3b8"
            mname = row.get("machine_name") or f"M-{row['machine_id']}"
            ts    = str(row["timestamp"])[:19]
            rows_html += (
                f"<tr>"
                f"<td style='padding:10px 14px;color:#64748b;font-size:12px;white-space:nowrap'>{ts}</td>"
                f"<td style='padding:10px 14px;color:#f1f5f9;font-weight:500'>{mname}</td>"
                f"<td style='padding:10px 14px;color:{color}'>{action}</td>"
                f"</tr>"
            )

        timeline_html = f"""<!DOCTYPE html>
<html><head><style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f172a; font-family: Inter, sans-serif; font-size: 13px; color: #cbd5e1; }}
  table {{ width: 100%; border-collapse: collapse; background: {CARD}; border-radius: 12px; overflow: hidden; }}
  thead tr {{ background: #0f172a; border-bottom: 2px solid {BORDER}; }}
  th {{ padding: 10px 14px; text-align: left; color: #64748b; font-size: 11px; font-weight: 700;
        letter-spacing: 0.05em; text-transform: uppercase; white-space: nowrap; }}
  td {{ border-bottom: 1px solid {BORDER}; vertical-align: middle; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover {{ background: rgba(255,255,255,0.03); }}
</style></head>
<body>
  <table>
    <thead><tr><th>Time</th><th>Machine</th><th>Event</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body></html>"""

        height = min(500, max(150, len(snap) * 44 + 55))
        components.html(timeline_html, height=height, scrolling=True)