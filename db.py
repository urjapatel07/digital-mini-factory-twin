import sqlite3
import pandas as pd
import os

# Resolve DB path relative to this file
_HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_HERE, "digital_twin.db")


def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def query(sql: str, params=()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


# ── Convenience loaders ───────────────────────────────────────────────────────

def get_production_lines():
    return query("SELECT * FROM production_lines")

def get_machines(line_id=None):
    if line_id:
        return query("SELECT * FROM machines WHERE line_id=?", (line_id,))
    return query("SELECT * FROM machines")

def get_alerts(status=None):
    if status and status != "All":
        return query("SELECT * FROM alerts WHERE status=? ORDER BY created_at DESC", (status,))
    return query("SELECT * FROM alerts ORDER BY created_at DESC")

def get_logs(line_id=None, machine_id=None):
    base = "SELECT l.*, m.machine_name, pl.line_name FROM logs l LEFT JOIN machines m ON l.machine_id=m.machine_id LEFT JOIN production_lines pl ON l.line_id=pl.line_id"
    conds, params = [], []
    if line_id:
        conds.append("l.line_id=?"); params.append(line_id)
    if machine_id:
        conds.append("l.machine_id=?"); params.append(machine_id)
    if conds:
        base += " WHERE " + " AND ".join(conds)
    base += " ORDER BY l.timestamp DESC"
    return query(base, params)

def get_production_data():
    return query("""
        SELECT pd.*, m.machine_name, m.line_id, pl.line_name
        FROM production_data pd
        LEFT JOIN machines m ON pd.machine_id=m.machine_id
        LEFT JOIN production_lines pl ON m.line_id=pl.line_id
    """)

def get_metrics():
    return query("""
        SELECT mt.*, pl.line_name
        FROM metrics mt
        LEFT JOIN production_lines pl ON mt.line_id=pl.line_id
    """)

def get_summary_kpis():
    machines = get_machines()
    alerts   = get_alerts()
    metrics  = get_metrics()
    return {
        "total_output":    int(machines["output"].sum()),
        "active_lines":    int((machines.groupby("line_id")["status"].apply(lambda s: (s=="Running").any())).sum()),
        "active_alerts":   int((alerts["status"] == "Active").sum()),
        "avg_efficiency":  round(machines["efficiency"].mean(), 1),
    }
