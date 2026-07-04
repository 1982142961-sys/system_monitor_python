"""
系统指标采集模块
支持 Windows / Linux / macOS，用 psutil 统一接口
"""

import psutil
import platform
import time
from datetime import datetime


def get_cpu_info():
    """获取 CPU 使用率和基本信息"""
    cpu_percent = psutil.cpu_percent(interval=0.5)       # 阻塞 0.5 秒采样
    cpu_count = psutil.cpu_count(logical=True)            # 逻辑核心数（含超线程）
    cpu_freq = psutil.cpu_freq()
    per_cpu = psutil.cpu_percent(interval=0, percpu=True) # 每核使用率

    return {
        "percent": cpu_percent,
        "cores": cpu_count,
        "freq_current": round(cpu_freq.current, 1) if cpu_freq else 0,
        "freq_max": round(cpu_freq.max, 1) if cpu_freq else 0,
        "per_core": per_cpu
    }


def get_memory_info():
    """获取内存使用情况"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total_gb":       round(mem.total / (1024**3), 1),
        "used_gb":        round(mem.used / (1024**3), 1),
        "available_gb":   round(mem.available / (1024**3), 1),
        "percent":        mem.percent,
        "swap_total_gb":  round(swap.total / (1024**3), 1),
        "swap_used_gb":   round(swap.used / (1024**3), 1),
        "swap_percent":   swap.percent
    }


def get_disk_info():
    """获取所有分区的磁盘使用情况"""
    disks = []
    for part in psutil.disk_partitions():
        # 跳过光驱和没有挂载点的设备
        if 'cdrom' in part.opts or part.fstype == '':
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device":      part.device,
                "mountpoint":  part.mountpoint,
                "fstype":      part.fstype,
                "total_gb":    round(usage.total / (1024**3), 1),
                "used_gb":     round(usage.used / (1024**3), 1),
                "free_gb":     round(usage.free / (1024**3), 1),
                "percent":     usage.percent
            })
        except PermissionError:
            continue
    return disks


def get_network_info():
    """获取网络 I/O 统计（累计值，前端做差值计算速率）"""
    net = psutil.net_io_counters()
    return {
        "bytes_sent_mb":     round(net.bytes_sent / (1024**2), 2),
        "bytes_recv_mb":     round(net.bytes_recv / (1024**2), 2),
        "packets_sent":      net.packets_sent,
        "packets_recv":      net.packets_recv,
        "timestamp":         time.time()
    }


def get_process_top(count=10):
    """获取 CPU 和内存消耗最高的进程"""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            info = p.info
            info['cpu_percent'] = info['cpu_percent'] or 0
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_cpu = sorted(procs, key=lambda x: x['cpu_percent'], reverse=True)[:count]
    top_mem = sorted(procs, key=lambda x: x['memory_percent'], reverse=True)[:count]

    return {
        "top_cpu": [{"name": p['name'], "pid": p['pid'], "value": p['cpu_percent']} for p in top_cpu],
        "top_mem": [{"name": p['name'], "pid": p['pid'], "value": round(p['memory_percent'], 1)} for p in top_mem]
    }


def get_system_info():
    """系统基本信息"""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    uptime = now - boot_time

    return {
        "hostname":    platform.node(),
        "os":          f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "python":      platform.python_version(),
        "boot_time":   boot_time.strftime("%Y-%m-%d %H:%M:%S"),
        "uptime":      str(uptime).split('.')[0]   # 去掉毫秒部分
    }


def get_all_metrics():
    """一次性获取所有指标，返回给前端"""
    return {
        "system":      get_system_info(),
        "cpu":         get_cpu_info(),
        "memory":      get_memory_info(),
        "disks":       get_disk_info(),
        "network":     get_network_info(),
        "processes":   get_process_top(8),
        "timestamp":   datetime.now().strftime("%H:%M:%S")
    }