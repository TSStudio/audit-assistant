# ---------- stage 1: build frontend ----------
FROM node:20-alpine AS fe_builder
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- stage 2: runtime (python + nginx) ----------
FROM modelscope-registry.cn-beijing.cr.aliyuncs.com/modelscope-repo/python:3.10

WORKDIR /home/user/app

# 安装 nginx
RUN apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends libzbar0

# 后端依赖
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# 拷贝后端代码
COPY backend/ ./backend/

# 拷贝前端 build 产物到 dist/
COPY --from=fe_builder /fe/dist ./dist

# Nginx 配置
COPY deploy/nginx.conf /etc/nginx/nginx.conf

# （可选）一些平台会探测这个端口；你的示例是 7860
EXPOSE 7860

# 同时启动 uvicorn 和 nginx
# uvicorn 跑在 127.0.0.1:8000；nginx 对外 7860 并反代 /api/
COPY start.sh /home/user/app/start.sh
RUN chmod +x /home/user/app/start.sh
ENTRYPOINT ["/home/user/app/start.sh"]