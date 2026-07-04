"""
SQLite 历史数据存储
metrics  表 —— 每分钟存一条系统指标快照
alerts   表 —— 超阈值告警记录
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "monitor.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS metrics (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    NOT NULL,
            cpu_percent   REAL,
            memory_percent REAL,
            swap_percent  REAL,
            disk_json     TEXT,
            net_sent_mb   REAL,
            net_recv_mb   REAL
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    NOT NULL,
            metric_type   TEXT    NOT NULL,
            value         REAL,
            threshold     REAL,
            message       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_time  ON alerts(timestamp);
    """)
    conn.commit()
    conn.close()


def insert_metrics(data: dict):
    conn = get_conn()
    conn.execute(
        """INSERT INTO metrics
           (timestamp, cpu_percent, memory_percent, swap_percent, disk_json, net_sent_mb, net_recv_mb)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data["timestamp"],
            data["cpu"]["percent"],
            data["memory"]["percent"],
            data["memory"]["swap_percent"],
            json.dumps(data["disks"], ensure_ascii=False),
            data["network"]["bytes_sent_mb"],
            data["network"]["bytes_recv_mb"],
        ),
    )
    conn.commit()
    conn.close()


def get_recent_metrics(minutes: int = 60):
    since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM metrics WHERE timestamp >= ? ORDER BY timestamp ASC", (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_alert(metric_type: str, value: float, threshold: float, message: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO alerts (timestamp, metric_type, value, threshold, message) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), metric_type, value, threshold, message),
    )
    conn.commit()
    conn.close()


def get_recent_alerts(minutes: int = 30):
    since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM alerts WHERE timestamp >= ? ORDER BY timestamp DESC", (since,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_old_data():
    """保留 24 小时指标、7 天告警"""
    conn = get_conn()
    conn.execute(
        "DELETE FROM metrics WHERE timestamp < ?",
        ((datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),),
    )
    conn.execute(
        "DELETE FROM alerts WHERE timestamp < ?",
        ((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),),
    )
    conn.commit()
    conn.close()