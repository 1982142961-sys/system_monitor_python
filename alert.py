"""
告警检测模块
检查 CPU / 内存 / 磁盘是否超过阈值
"""

from database import insert_alert, get_recent_alerts

# 阈值配置
CPU_THRESHOLD = 90       # CPU 使用率超过 90%
MEM_THRESHOLD = 90       # 内存使用率超过 90%
DISK_THRESHOLD = 90      # 磁盘使用率超过 90%

# 防重复告警：同类型告警 5 分钟内不重复发
COOLDOWN_MINUTES = 5


def check_alerts(data: dict):
    """检测所有指标是否超阈值，返回本次触发的告警列表"""
    triggered = []

    cpu_pct = data["cpu"]["percent"]
    mem_pct = data["memory"]["percent"]
    swap_pct = data["memory"]["swap_percent"]

    # CPU
    if cpu_pct > CPU_THRESHOLD:
        msg = f"CPU 使用率 {cpu_pct:.1f}% 超过阈值 {CPU_THRESHOLD}%"
        if not _is_cooldown("cpu"):
            insert_alert("cpu", cpu_pct, CPU_THRESHOLD, msg)
            triggered.append({"type": "cpu", "message": msg})

    # 内存
    if mem_pct > MEM_THRESHOLD:
        msg = f"内存使用率 {mem_pct:.1f}% 超过阈值 {MEM_THRESHOLD}%"
        if not _is_cooldown("memory"):
            insert_alert("memory", mem_pct, MEM_THRESHOLD, msg)
            triggered.append({"type": "memory", "message": msg})

    # Swap
    if swap_pct > MEM_THRESHOLD:
        msg = f"Swap 使用率 {swap_pct:.1f}% 超过阈值 {MEM_THRESHOLD}%"
        if not _is_cooldown("swap"):
            insert_alert("swap", swap_pct, MEM_THRESHOLD, msg)
            triggered.append({"type": "swap", "message": msg})

    # 磁盘
    for disk in data["disks"]:
        if disk["percent"] > DISK_THRESHOLD:
            msg = f"磁盘 {disk['mountpoint']} 使用率 {disk['percent']:.1f}% 超过阈值 {DISK_THRESHOLD}%"
            key = f"disk_{disk['mountpoint']}"
            if not _is_cooldown(key):
                insert_alert("disk", disk["percent"], DISK_THRESHOLD, msg)
                triggered.append({"type": "disk", "message": msg})

    return triggered


def _is_cooldown(metric_type: str) -> bool:
    """检查最近 COOLDOWN_MINUTES 分钟内是否已有同类型告警"""
    recent = get_recent_alerts(COOLDOWN_MINUTES)
    return any(a["metric_type"] == metric_type for a in recent)