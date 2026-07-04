"""
Flask 后端 —— 提供页面和 API
启动后访问 http://localhost:5000
"""

from flask import Flask, render_template, jsonify
from monitor import get_all_metrics

app = Flask(__name__)


@app.route("/")
def dashboard():
    """主页面 —— 渲染仪表盘"""
    return render_template("dashboard.html")


@app.route("/api/metrics")
def api_metrics():
    """JSON 接口 —— 返回所有系统指标"""
    try:
        data = get_all_metrics()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # debug=True 开启热重载（改代码自动重启）
    # host="0.0.0.0" 允许局域网其他设备访问
    app.run(host="0.0.0.0", port=5000, debug=True)