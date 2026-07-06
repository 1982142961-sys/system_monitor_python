"""
数据库存储层
支持 SQLite / MySQL 切换，通过 config.yaml 中 database.type 控制。

表结构：
- metrics   —— 系统指标快照
- alerts    —— 超阈值告警记录
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from config import get


# ═══════════════════════════════════════════════════════════════
# 抽象接口
# ═══════════════════════════════════════════════════════════════

class DatabaseBackend(ABC):
    """数据库后端统一接口。"""

    @abstractmethod
    def init(self): ...

    @abstractmethod
    def insert_metrics(self, data: dict): ...

    @abstractmethod
    def get_recent_metrics(self, minutes: int) -> list[dict]: ...

    @abstractmethod
    def insert_alert(self, metric_type: str, value: float, threshold: float, message: str): ...

    @abstractmethod
    def get_recent_alerts(self, minutes: int) -> list[dict]: ...

    @abstractmethod
    def cleanup(self): ...


# ═══════════════════════════════════════════════════════════════
# SQLite 实现
# ═══════════════════════════════════════════════════════════════

class SQLiteBackend(DatabaseBackend):
    def __init__(self):
        import sqlite3
        self._db_path = get("database.sqlite.path", "monitor.db")
        self._connector = sqlite3

    def _conn(self):
        conn = self._connector.connect(self._db_path)
        conn.row_factory = self._connector.Row
        return conn

    def init(self):
        conn = self._conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                cpu_percent     REAL,
                memory_percent  REAL,
                swap_percent    REAL,
                disk_json       TEXT,
                net_sent_mb     REAL,
                net_recv_mb     REAL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp       TEXT    NOT NULL,
                metric_type     TEXT    NOT NULL,
                value           REAL,
                threshold       REAL,
                message         TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_time  ON alerts(timestamp);
        """)
        conn.commit()
        conn.close()

    def insert_metrics(self, data: dict):
        conn = self._conn()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """INSERT INTO metrics
               (timestamp, cpu_percent, memory_percent, swap_percent, disk_json, net_sent_mb, net_recv_mb)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ts,
             data["cpu"]["percent"],
             data["memory"]["percent"],
             data["memory"]["swap_percent"],
             json.dumps(data["disks"], ensure_ascii=False),
             data["network"]["bytes_sent_mb"],
             data["network"]["bytes_recv_mb"]))
        conn.commit()
        conn.close()

    def get_recent_metrics(self, minutes: int):
        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM metrics WHERE timestamp >= ? ORDER BY timestamp ASC", (since,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def insert_alert(self, metric_type: str, value: float, threshold: float, message: str):
        conn = self._conn()
        conn.execute(
            "INSERT INTO alerts (timestamp, metric_type, value, threshold, message) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), metric_type, value, threshold, message))
        conn.commit()
        conn.close()

    def get_recent_alerts(self, minutes: int):
        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM alerts WHERE timestamp >= ? ORDER BY timestamp DESC", (since,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def cleanup(self):
        conn = self._conn()
        conn.execute(
            "DELETE FROM metrics WHERE timestamp < ?",
            ((datetime.now() - timedelta(hours=get("retention.metrics_hours", 24))).strftime("%Y-%m-%d %H:%M:%S"),))
        conn.execute(
            "DELETE FROM alerts WHERE timestamp < ?",
            ((datetime.now() - timedelta(days=get("retention.alerts_days", 7))).strftime("%Y-%m-%d %H:%M:%S"),))
        conn.commit()
        conn.close()


# ═══════════════════════════════════════════════════════════════
# MySQL 实现
# ═══════════════════════════════════════════════════════════════

class MySQLBackend(DatabaseBackend):
    def __init__(self):
        import pymysql
        self._connector = pymysql
        self._params = {
            "host":     get("database.mysql.host", "127.0.0.1"),
            "port":     get("database.mysql.port", 3306),
            "user":     get("database.mysql.user", "root"),
            "password": get("database.mysql.password", ""),
            "database": get("database.mysql.database", "sysmonitor"),
            "charset":  get("database.mysql.charset", "utf8mb4"),
            "autocommit": True,
        }

    def _conn(self):
        return self._connector.connect(**self._params)

    def init(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id              INT AUTO_INCREMENT PRIMARY KEY,
                timestamp       DATETIME NOT NULL,
                cpu_percent     DOUBLE,
                memory_percent  DOUBLE,
                swap_percent    DOUBLE,
                disk_json       TEXT,
                net_sent_mb     DOUBLE,
                net_recv_mb     DOUBLE,
                INDEX idx_metrics_time (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id              INT AUTO_INCREMENT PRIMARY KEY,
                timestamp       DATETIME NOT NULL,
                metric_type     VARCHAR(32) NOT NULL,
                value           DOUBLE,
                threshold       DOUBLE,
                message         TEXT,
                INDEX idx_alerts_time (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.close()

    def insert_metrics(self, data: dict):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO metrics
               (timestamp, cpu_percent, memory_percent, swap_percent, disk_json, net_sent_mb, net_recv_mb)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             data["cpu"]["percent"],
             data["memory"]["percent"],
             data["memory"]["swap_percent"],
             json.dumps(data["disks"], ensure_ascii=False),
             data["network"]["bytes_sent_mb"],
             data["network"]["bytes_recv_mb"]))
        conn.close()

    def get_recent_metrics(self, minutes: int):
        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM metrics WHERE timestamp >= %s ORDER BY timestamp ASC", (since,))
        columns = [col[0] for col in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return rows

    def insert_alert(self, metric_type: str, value: float, threshold: float, message: str):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO alerts (timestamp, metric_type, value, threshold, message) VALUES (%s, %s, %s, %s, %s)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), metric_type, value, threshold, message))
        conn.close()

    def get_recent_alerts(self, minutes: int):
        since = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM alerts WHERE timestamp >= %s ORDER BY timestamp DESC", (since,))
        columns = [col[0] for col in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.close()
        return rows

    def cleanup(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM metrics WHERE timestamp < %s",
            ((datetime.now() - timedelta(hours=get("retention.metrics_hours", 24))).strftime("%Y-%m-%d %H:%M:%S"),))
        cur.execute(
            "DELETE FROM alerts WHERE timestamp < %s",
            ((datetime.now() - timedelta(days=get("retention.alerts_days", 7))).strftime("%Y-%m-%d %H:%M:%S"),))
        conn.close()


# ═══════════════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════════════

_db: DatabaseBackend | None = None


def get_db() -> DatabaseBackend:
    """获取数据库后端实例（单例）。"""
    global _db
    if _db is not None:
        return _db

    db_type = get("database.type", "sqlite")
    if db_type == "mysql":
        _db = MySQLBackend()
    else:
        _db = SQLiteBackend()
    return _db


# ═══════════════════════════════════════════════════════════════
# 便捷函数（保持外部调用方式不变）
# ═══════════════════════════════════════════════════════════════

def init_db():
    get_db().init()


def insert_metrics(data: dict):
    get_db().insert_metrics(data)


def get_recent_metrics(minutes: int = 60) -> list[dict]:
    return get_db().get_recent_metrics(minutes)


def insert_alert(metric_type: str, value: float, threshold: float, message: str):
    get_db().insert_alert(metric_type, value, threshold, message)


def get_recent_alerts(minutes: int = 30) -> list[dict]:
    return get_db().get_recent_alerts(minutes)


def cleanup_old_data():
    get_db().cleanup()