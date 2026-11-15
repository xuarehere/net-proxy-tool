FROM python:3.11-alpine

LABEL maintainer="xuarehere"
LABEL description="net-proxy-tool: Cross-Platform Native Proxy Orchestrator"

# 安装 OpenSSH 客户端与 bash (用于节点 SSH 接入与探活)
RUN apk add --no-cache openssh-client bash curl

WORKDIR /app

# 拷贝应用代码与配置模板
COPY config.example.json /app/config.example.json
COPY with_proxy.py /app/with_proxy.py
COPY sdk /app/sdk
COPY bin /app/bin
COPY web /app/web
COPY gateway-watchdog /app/gateway-watchdog

# 保证数据持久化目录存在
RUN mkdir -p /app/data && chmod -R 755 /app/bin

EXPOSE 8899

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:8899/api/config || exit 1

ENTRYPOINT ["python3", "web/server.py"]
