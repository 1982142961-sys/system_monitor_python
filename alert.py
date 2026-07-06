"""
告警检测模块
检查 CPU / 内存 / 磁盘是否超过阈值，阈值从 config.yaml 读取。
"""

from database import insert_alert, get_recent_alerts
from config import get

# 阈值从配置文件读取，模块加载时取值一次

def check_alerts(data: dict):
    """检测所有指标是否超阈值，返回本次触发的告警列表。"""
    cpu_threshold = get("alert.cpu_threshold", 90)
    mem_threshold  = get("alert.memory_threshold", 90)
    disk_threshold = get("alert.disk_threshold", 90)
    cooldown       = get("alert.cooldown_minutes", 5)

    triggered = []

    cpu_pct = data["cpu"]["percent"]
    mem_pct = data["memory"]["percent"]
    swap_pct = data["memory"]["swap_percent"]

    # CPU
    if cpu_pct > cpu_threshold:
        msg = f"CPU 使用率 {cpu_pct:.1f}% 超过阈值 {cpu_threshold}%"
        if not _is_cooldown("cpu", cooldown):
            insert_alert("cpu", cpu_pct, cpu_threshold, msg)
            triggered.append({"type": "cpu", "message": msg})

    # 内存
    if mem_pct > mem_threshold:
        msg = f"内存使用率 {mem_pct:.1f}% 超过阈值 {mem_threshold}%"
        if not _is_cooldown("memory", cooldown):
            insert_alert("memory", mem_pct, mem_threshold, msg)
            triggered.append({"type": "memory", "message": msg})

    # Swap
    if swap_pct > mem_threshold:
        msg = f"Swap 使用率 {swap_pct:.1f}% 超过阈值 {mem_threshold}%"
        if not _is_cooldown("swap", cooldown):
            insert_alert("swap", swap_pct, mem_threshold, msg)
            triggered.append({"type": "swap", "message": msg})

    # 磁盘
    for disk in data["disks"]:
        if disk["percent"] > disk_threshold:
            msg = f"磁盘 {disk['mountpoint']} 使用率 {disk['percent']:.1f}% 超过阈值 {disk_threshold}%"
            key = f"disk_{disk['mountpoint']}"
            if not _is_cooldown(key, cooldown):
                insert_alert("disk", disk["percent"], disk_threshold, msg)
                triggered.append({"type": "disk", "message": msg})

    return triggered


def _is_cooldown(metric_type: str, minutes: int) -> bool:
    """检查最近 N 分钟内是否已有同类型告警。"""
    recent = get_recent_alerts(minutes)
    return any(a["metric_type"] == metric_type for a in recent)