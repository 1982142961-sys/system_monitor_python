FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源码
COPY . .

EXPOSE 5000

# 默认使用 SQLite，可通过挂载 config.yaml 覆盖
CMD ["python", "app.py"]