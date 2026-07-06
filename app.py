"""
Flask + WebSocket 后端
- WebSocket 实时推送指标到前端
- 定时入库保存历史
- 超阈值告警检测
- CSV 数据导出

启动：python app.py
配置：config.yaml
"""

import csv
import io
import threading
import time

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO

from config import get
from monitor import get_all_metrics
from database import init_db, insert_metrics, get_recent_metrics, get_recent_alerts, cleanup_old_data
from alert import check_alerts

app = Flask(__name__)
app.config["SECRET_KEY"] = "sysmonitor-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# 全局变量
_latest_data: dict = {}
_db_ticks = 0


# ── 后台采集线程 ──────────────────────────────────────

def _collect_loop():
    global _latest_data, _db_ticks
    init_db()
    cleanup_old_data()

    interval     = get("collector.interval_seconds", 3)
    db_save_ticks = get("collector.db_save_ticks", 3)

    while True:
        try:
            data = get_all_metrics()
            _latest_data = data

            # WebSocket 推送
            socketio.emit("metrics_update", data)

            # 定时入库 + 告警
            _db_ticks += 1
            if _db_ticks >= db_save_ticks:
                _db_ticks = 0
                insert_metrics(data)
                print(f"[DB] 已入库, CPU={data['cpu']['percent']:.1f}%, MEM={data['memory']['percent']:.1f}%")
                cleanup_old_data()

                triggered = check_alerts(data)
                if triggered:
                    socketio.emit("alert", {"alerts": triggered})
        except Exception as e:
            print(f"[collector] 采集异常: {e}")
        time.sleep(interval)


# ── 路由 ──────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/metrics")
def api_metrics():
    try:
        return jsonify(_latest_data or get_all_metrics())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history")
def api_history():
    rows = get_recent_metrics(60)
    return jsonify(rows)


@app.route("/api/alerts")
def api_alerts():
    rows = get_recent_alerts(30)
    return jsonify(rows)


@app.route("/api/export")
def api_export():
    """导出历史数据，支持 ?format=csv（默认）或 ?format=json。"""
    fmt = request.args.get("format", "csv").lower()
    minutes = request.args.get("minutes", 60, type=int)
    rows = get_recent_metrics(minutes)

    if fmt == "json":
        return jsonify(rows)

    # CSV 导出
    if not rows:
        return Response("无数据可导出", mimetype="text/plain; charset=utf-8")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "cpu_percent", "memory_percent", "swap_percent", "net_sent_mb", "net_recv_mb"])
    for r in rows:
        writer.writerow([
            r.get("timestamp", ""),
            r.get("cpu_percent", ""),
            r.get("memory_percent", ""),
            r.get("swap_percent", ""),
            r.get("net_sent_mb", ""),
            r.get("net_recv_mb", ""),
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=sysmonitor_export.csv"}
    )


# ── WebSocket 事件 ────────────────────────────────────

@socketio.on("connect")
def on_connect():
    if _latest_data:
        socketio.emit("metrics_update", _latest_data)
    history = get_recent_metrics(60)
    socketio.emit("history_data", history)


# ── 启动 ──────────────────────────────────────────────

if __name__ == "__main__":
    host  = get("server.host", "0.0.0.0")
    port  = get("server.port", 5000)
    debug = get("server.debug", False)

    threading.Thread(target=_collect_loop, daemon=True).start()
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)