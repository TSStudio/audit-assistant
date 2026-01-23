#!/bin/sh
set -e

# 启动 FastAPI（后台）
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &

# 启动 Nginx（前台）
exec nginx -g "daemon off;"