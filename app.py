"""
Flask + WebSocket 后端
- WebSocket 实时推送指标到前端
- 每分钟自动入库保存历史
- 超阈值告警检测
启动后访问 http://localhost:5000
"""

import threading
import time
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

from monitor import get_all_metrics
from database import init_db, insert_metrics, get_recent_metrics, get_recent_alerts, cleanup_old_data
from alert import check_alerts

app = Flask(__name__)
app.config["SECRET_KEY"] = "sysmonitor-secret"
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量：保存最新一次采集结果（后台线程写，API 读）
_latest_data: dict = {}
_db_ticks = 0  # 计数器，每 20 次（约 60 秒）入库一次


# ── 后台采集线程 ──────────────────────────────────────

def _collect_loop():
    global _latest_data, _db_ticks
    init_db()
    cleanup_old_data()
    while True:
        try:
            data = get_all_metrics()
            _latest_data = data

            # 每 3 秒通过 WebSocket 推送
            socketio.emit("metrics_update", data)

            # 每 60 秒入库 + 告警检测
            _db_ticks += 1
            if _db_ticks >= 20:
                _db_ticks = 0
                insert_metrics(data)
                cleanup_old_data()

                # 告警检测
                triggered = check_alerts(data)
                if triggered:
                    socketio.emit("alert", {"alerts": triggered})
        except Exception as e:
            print(f"[collector] 采集异常: {e}")
        time.sleep(3)


# ── 路由 ──────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/metrics")
def api_metrics():
    """REST 备用接口"""
    try:
        return jsonify(_latest_data or get_all_metrics())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history")
def api_history():
    """返回最近 60 分钟的历史数据，供前端趋势图"""
    rows = get_recent_metrics(60)
    return jsonify(rows)


@app.route("/api/alerts")
def api_alerts():
    """返回最近 30 分钟的告警"""
    rows = get_recent_alerts(30)
    return jsonify(rows)


# ── WebSocket 事件 ────────────────────────────────────

@socketio.on("connect")
def on_connect():
    """客户端连接后立即发送最新数据"""
    if _latest_data:
        socketio.emit("metrics_update", _latest_data)
    # 同时发送历史数据
    history = get_recent_metrics(60)
    socketio.emit("history_data", history)


# ── 启动 ──────────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=_collect_loop, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)