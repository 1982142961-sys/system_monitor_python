# SysMonitor —— Python 系统资源监控仪表盘

> Flask + WebSocket + ECharts + SQLite/MySQL + Docker

浏览器打开后自动展示 CPU、内存、磁盘、网络、进程等指标的动态图表，WebSocket 实时推送，支持历史趋势回看、超阈值告警、CSV 数据导出。

---

## 功能亮点

- **WebSocket 实时推送** —— 数据主动推送到浏览器，不轮询
- **历史趋势图** —— 最近 60 分钟 CPU / 内存折线图，支持拖拽缩放
- **超阈值告警** —— CPU / 内存 / 磁盘超 90% 自动提醒，5 分钟防重复
- **数据持久化** —— SQLite（默认）或 MySQL，每分钟自动入库
- **CSV 导出** —— `/api/export?format=csv` 一键下载历史数据
- **配置分离** —— 所有参数集中在 `config.yaml`，修改无需改代码
- **Docker 一键部署** —— 自带 Dockerfile 和 docker-compose.yml

---

## 快速开始

### 方式一：Docker（推荐）

```bash
docker compose up -d
# → http://localhost:5000
```

### 方式二：本地 Python

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5000
```

### 运行测试

```bash
pip install pytest
pytest tests/ -v
```

---

## 配置说明（config.yaml）

```yaml
database:
  type: "sqlite"             # "sqlite" 或 "mysql"

  mysql:                     # type: mysql 时生效
    host: "127.0.0.1"
    port: 3306
    user: "root"
    password: ""
    database: "sysmonitor"

alert:
  cpu_threshold: 90          # CPU 告警阈值（%）
  memory_threshold: 90       # 内存告警阈值（%）
  disk_threshold: 90         # 磁盘告警阈值（%）
  cooldown_minutes: 5        # 同类型告警冷却（分钟）

retention:
  metrics_hours: 24          # 指标保留时长
  alerts_days: 7             # 告警保留时长
```

MySQL 模式需提前建库：

```sql
CREATE DATABASE sysmonitor DEFAULT CHARACTER SET utf8mb4;
```

---

## 项目结构

```
system_monitor/
├── app.py                  # Flask + WebSocket 主程序
├── config.yaml             # 配置文件（阈值、端口、数据库等）
├── config.py               # 配置加载模块
├── monitor.py              # 系统指标采集（psutil）
├── database.py             # 存储层（SQLite / MySQL 双后端）
├── alert.py                # 告警检测模块
├── requirements.txt        # Python 依赖
├── test_monitor.py         # 快速冒烟测试
├── tests/
│   └── test_all.py         # 单元测试（pytest）
├── Dockerfile
├── docker-compose.yml
├── templates/
│   └── dashboard.html      # ECharts + WebSocket 前端
├── static/
│   └── style.css           # 深色主题样式
└── README.md
```

---

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /` | 仪表盘页面 |
| `GET /api/metrics` | 最新系统指标 JSON |
| `GET /api/history` | 最近 60 分钟历史数据 |
| `GET /api/alerts` | 最近 30 分钟告警记录 |
| `GET /api/export?format=csv` | 导出 CSV（支持 `&minutes=120`） |

WebSocket 事件：
- `metrics_update` —— 实时指标推送
- `history_data` —— 历史数据（连接时推送）
- `alert` —— 超阈值告警

---

## 数据流

```
后台线程（每 3 秒采集）
    │
    ├──→ WebSocket emit ──→ 浏览器实时更新图表
    │
    ├──→ 定时写入 DB ──→ /api/history 回查趋势
    │
    ├──→ 超阈值检测 ──→ WebSocket alert ──→ 浏览器弹窗
    │
    └──→ CSV 导出 ──→ /api/export
```

---

## 技术栈

| 层 | 技术 |
|------|------|
| 后端 | Python 3 + Flask + Flask-SocketIO |
| 实时通信 | WebSocket |
| 系统指标 | psutil（跨平台） |
| 存储 | SQLite / MySQL（可切换） |
| 配置 | YAML（config.yaml） |
| 前端图表 | ECharts 5（CDN） |
| 样式 | 纯 CSS Grid + 深色主题 |
| 部署 | Docker + docker-compose |
| 测试 | pytest |

---

## 许可

MIT