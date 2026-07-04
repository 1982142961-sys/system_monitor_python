# SysMonitor —— Python 系统资源监控仪表盘

基于 **Flask + WebSocket + ECharts + SQLite** 的实时系统监控仪表盘，支持 Windows / Linux / macOS。

浏览器打开后自动展示 CPU、内存、磁盘、网络、进程等指标的动态图表，WebSocket 实时推送，支持历史趋势回看和超阈值告警。

---

## 功能亮点

- **WebSocket 实时推送** —— 不再轮询，数据主动推到浏览器
- **历史趋势图** —— 最近 60 分钟 CPU / 内存折线图，可拖拽缩放
- **超阈值告警** —— CPU、内存、磁盘超过 90% 自动弹窗提醒，5 分钟防重复
- **SQLite 持久化** —— 每分钟自动入库，24 小时历史可查
- **Docker 一键部署** —— 自带 Dockerfile 和 docker-compose.yml

---

## 截图

启动后访问 `http://localhost:5000`，你将看到：

- **CPU 仪表盘** —— 实时使用率 + 颜色渐变（绿→橙→红）
- **CPU / 内存历史折线图** —— 最近 60 分钟趋势
- **各核心柱状图** —— 每核 CPU 负载分布
- **内存 & Swap 仪表盘** —— 已用/总量
- **磁盘使用** —— 各分区占用百分比
- **进程 TOP 榜** —— CPU 和内存消耗最高的进程
- **告警弹窗** —— 超阈值时右上角弹出红色提醒

---

## 快速开始

### 方式一：Docker（推荐）

```bash
docker compose up -d
```

浏览器打开 `http://localhost:5000`。

### 方式二：本地 Python

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python app.py

# 3. 打开浏览器
# http://localhost:5000
```

### 快速测试（不启动网页）

```bash
python test_monitor.py
```

---

## 项目结构

```
system_monitor/
├── app.py                  # Flask + WebSocket 主程序
├── monitor.py              # 系统指标采集（psutil）
├── database.py             # SQLite 存储层
├── alert.py                # 告警检测模块
├── requirements.txt        # Python 依赖
├── test_monitor.py         # 独立测试脚本
├── Dockerfile              # Docker 镜像
├── docker-compose.yml      # Docker 一键部署
├── templates/
│   └── dashboard.html      # ECharts + WebSocket 前端
├── static/
│   └── style.css           # 深色主题样式
└── README.md
```

---

## 数据流

```
后台线程（每 3 秒采集）
    │
    ├──→ WebSocket emit ←── 浏览器实时更新图表
    │
    ├──→ 每 60 秒写入 SQLite ──→ /api/history 回查
    │
    └──→ 超阈值检测 ──→ WebSocket alert ──→ 浏览器弹窗
```

---

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /` | 仪表盘页面 |
| `GET /api/metrics` | 最新系统指标 JSON |
| `GET /api/history` | 最近 60 分钟历史数据 |
| `GET /api/alerts` | 最近 30 分钟告警记录 |

WebSocket 事件：
- 客户端连接后自动推送 `metrics_update`（实时指标）和 `history_data`（历史数据）
- 超阈值时推送 `alert`（告警信息）

---

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3 + Flask + Flask-SocketIO |
| 实时通信 | WebSocket |
| 系统指标 | psutil（跨平台） |
| 存储 | SQLite |
| 前端图表 | ECharts 5（CDN） |
| 样式 | 纯 CSS Grid + 深色主题 |
| 部署 | Docker + docker-compose |

---

## 许可

MIT License