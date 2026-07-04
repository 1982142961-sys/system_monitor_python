import json
from monitor import get_all_metrics

data = get_all_metrics()
print("主机名:", data["system"]["hostname"])
print("OS:", data["system"]["os"])
print("运行时间:", data["system"]["uptime"])
print("CPU:", data["cpu"]["percent"], "%  (", data["cpu"]["cores"], "核)")
print("内存:", data["memory"]["percent"], "%  (", data["memory"]["used_gb"], "/", data["memory"]["total_gb"], "GB)")
print("磁盘数:", len(data["disks"]))
for d in data["disks"]:
    print(f"  {d['mountpoint']}: {d['percent']}% ({d['used_gb']}/{d['total_gb']} GB)")
print("TOP CPU进程:", [p["name"] for p in data["processes"]["top_cpu"][:3]])
print("TOP MEM进程:", [p["name"] for p in data["processes"]["top_mem"][:3]])
print("\n所有模块工作正常")