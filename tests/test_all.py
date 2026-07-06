"""
单元测试 —— 覆盖 monitor（psutil 封装）、alert（阈值检测）、database（SQLite 读写清）。
使用 pytest 运行：pytest tests/ -v
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# 确保项目根在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ══════════════════════════════════════════════════════════
# monitor 模块测试
# ══════════════════════════════════════════════════════════

import monitor


class TestMonitor:
    """测试系统指标采集模块（依赖 psutil）。"""

    def test_get_all_metrics_return_keys(self):
        """返回的字典应包含所有顶层键。"""
        data = monitor.get_all_metrics()
        for key in ["system", "cpu", "memory", "disks", "network", "processes", "timestamp"]:
            assert key in data, f"缺少键: {key}"

    def test_cpu_info_structure(self):
        data = monitor.get_cpu_info()
        assert 0 <= data["percent"] <= 100
        assert data["cores"] > 0
        assert isinstance(data["per_core"], list)

    def test_memory_info_structure(self):
        data = monitor.get_memory_info()
        assert 0 <= data["percent"] <= 100
        assert data["total_gb"] > 0
        assert data["swap_percent"] >= 0

    def test_disk_info_is_list(self):
        disks = monitor.get_disk_info()
        assert isinstance(disks, list)
        if disks:
            assert "mountpoint" in disks[0]
            assert "percent" in disks[0]

    def test_network_info_has_keys(self):
        net = monitor.get_network_info()
        for key in ["bytes_sent_mb", "bytes_recv_mb", "timestamp"]:
            assert key in net

    def test_process_top_structure(self):
        procs = monitor.get_process_top(5)
        assert "top_cpu" in procs
        assert "top_mem" in procs
        assert len(procs["top_cpu"]) <= 5

    def test_system_info_basic(self):
        sysinfo = monitor.get_system_info()
        assert sysinfo["hostname"]
        assert sysinfo["os"]


# ══════════════════════════════════════════════════════════
# alert 模块测试
# ══════════════════════════════════════════════════════════

import alert
from database import DatabaseBackend


class FakeDB(DatabaseBackend):
    """内存模拟数据库，用于 alert 测试。"""
    def __init__(self):
        self.alerts: list[dict] = []

    def init(self): pass
    def cleanup(self): pass

    def insert_metrics(self, data): pass

    def get_recent_metrics(self, minutes):
        return []

    def insert_alert(self, metric_type, value, threshold, message):
        self.alerts.append({
            "metric_type": metric_type,
            "value": value,
            "threshold": threshold,
            "message": message,
        })

    def get_recent_alerts(self, minutes):
        return self.alerts


class TestAlert:
    """测试告警检测逻辑。"""

    def _make_data(self, cpu=50.0, mem=50.0, swap=0.0, disks=None):
        return {
            "cpu": {"percent": cpu},
            "memory": {"percent": mem, "swap_percent": swap},
            "disks": disks or [],
        }

    def test_no_alert_when_all_normal(self):
        data = self._make_data(cpu=30, mem=40)
        result = alert.check_alerts(data)
        assert result == []

    def test_cpu_alert_triggered(self):
        data = self._make_data(cpu=95)
        # 用 monkeypatch 换掉数据库，避免写真实 DB
        fake = FakeDB()
        with patch("alert.insert_alert", fake.insert_alert), \
             patch("alert.get_recent_alerts", fake.get_recent_alerts):
            result = alert.check_alerts(data)
            assert len(result) >= 1
            assert result[0]["type"] == "cpu"

    def test_memory_alert_triggered(self):
        data = self._make_data(mem=95)
        fake = FakeDB()
        with patch("alert.insert_alert", fake.insert_alert), \
             patch("alert.get_recent_alerts", fake.get_recent_alerts):
            result = alert.check_alerts(data)
            assert len(result) >= 1
            assert result[0]["type"] == "memory"

    def test_disk_alert_triggered(self):
        data = self._make_data(disks=[
            {"mountpoint": "/", "percent": 95, "total_gb": 100, "used_gb": 95, "free_gb": 5}
        ])
        fake = FakeDB()
        with patch("alert.insert_alert", fake.insert_alert), \
             patch("alert.get_recent_alerts", fake.get_recent_alerts):
            result = alert.check_alerts(data)
            assert len(result) >= 1
            assert result[0]["type"] == "disk"

    def test_cooldown_prevents_duplicate(self):
        """同类型告警在冷却期内不重复触发。"""
        data = self._make_data(cpu=95)
        fake = FakeDB()
        # 先插入一条 CPU 告警
        fake.insert_alert("cpu", 95, 90, "test")
        with patch("alert.insert_alert", fake.insert_alert), \
             patch("alert.get_recent_alerts", fake.get_recent_alerts):
            result = alert.check_alerts(data)
            assert result == []  # 冷却期，不再触发


# ══════════════════════════════════════════════════════════
# database 模块测试
# ══════════════════════════════════════════════════════════

import database as db_module


class TestDatabase:
    """测试 SQLite 数据库操作。"""

    @classmethod
    def setup_class(cls):
        # 用临时文件替换真实数据库
        cls._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls._tmp_path = cls._tmp.name

        # 重置单例
        db_module._db = None

        # patch 数据库路径
        cls._patch = patch.object(
            db_module.SQLiteBackend, "_conn",
            lambda self: cls._make_conn(cls._tmp_path)
        )
        cls._patch.start()

        db_module.init_db()

    @classmethod
    def teardown_class(cls):
        cls._patch.stop()
        os.unlink(cls._tmp_path)

    @staticmethod
    def _make_conn(path):
        import sqlite3
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    def _sample_metrics(self):
        return {
            "cpu": {"percent": 45.2},
            "memory": {"percent": 60.1, "swap_percent": 10.0},
            "disks": [{"mountpoint": "/", "percent": 70, "total_gb": 100, "used_gb": 70, "free_gb": 30}],
            "network": {"bytes_sent_mb": 100.5, "bytes_recv_mb": 200.3},
        }

    def test_insert_and_query_metrics(self):
        db_module.insert_metrics(self._sample_metrics())
        rows = db_module.get_recent_metrics(60)
        assert len(rows) >= 1
        row = rows[-1]
        assert row["cpu_percent"] == 45.2
        assert row["memory_percent"] == 60.1
        # disk_json 可反序列化
        disks = json.loads(row["disk_json"])
        assert len(disks) == 1

    def test_insert_and_query_alerts(self):
        db_module.insert_alert("cpu", 95.0, 90.0, "test alert")
        alerts = db_module.get_recent_alerts(60)
        assert len(alerts) >= 1
        a = alerts[0]
        assert a["metric_type"] == "cpu"
        assert a["value"] == 95.0

    def test_cleanup_does_not_crash(self):
        db_module.cleanup_old_data()