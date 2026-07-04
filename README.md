# SysMonitor —— Python 系统资源监控仪表盘

基于 **Flask + ECharts + psutil** 的实时系统监控仪表盘，支持 Windows / Linux / macOS。

浏览器打开后自动展示 CPU、内存、磁盘、网络、进程等指标的动态图表，每 3 秒自动刷新。

---

## 截图

启动后访问 `http://localhost:5000`，你将看到：

- **CPU 仪表盘** —— 实时使用率 + 颜色渐变（绿→橙→红）
- **各核心柱状图** —— 每核 CPU 负载分布
- **内存 & Swap 仪表盘** —— 已用/总量
- **磁盘使用** —— 各分区占用百分比
- **进程 TOP 榜** —— CPU 和内存消耗最高的 8 个进程

---

## 快速开始

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 启动

```bash
python app.py
```

### 3. 打开浏览器

```
http://localhost:5000
```

---

## 项目结构

```
system_monitor/
├── app.py                  # Flask 主程序（页面 + API）
├── monitor.py              # 系统指标采集（psutil）
├── requirements.txt        # Python 依赖
├── templates/
│   └── dashboard.html      # ECharts 前端（CDN 加载，无需本地安装）
├── static/
│   └── style.css           # 深色主题样式
└── README.md
```

---

## API 接口

### `GET /api/metrics`

返回 JSON 格式的全部系统指标：

```json
{
  "system": {
    "hostname": "DESKTOP-xxx",
    "os": "Windows 10.0.19045",
    "uptime": "2:15:30"
  },
  "cpu": {
    "percent": 23.5,
    "cores": 8,
    "per_core": [12, 45, 8, 30, ...]
  },
  "memory": {
    "total_gb": 16.0,
    "used_gb": 6.2,
    "percent": 38.8
  },
  "disks": [
    {"mountpoint": "C:/", "percent": 65, "total_gb": 256, "used_gb": 166}
  ],
  "processes": {
    "top_cpu": [{"name": "chrome.exe", "pid": 1234, "value": 12.5}, ...],
    "top_mem": [...]
  }
}
```

---

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3 + Flask |
| 系统指标 | psutil（跨平台） |
| 前端图表 | ECharts 5（CDN） |
| 数据刷新 | AJAX 轮询（3 秒间隔） |
| 样式 | 纯 CSS Grid + 深色主题 |

---

## 许可

MIT License