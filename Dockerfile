FROM python:3.12-alpine
RUN apk add --no-cache openssh-client bash curl \
    && addgroup -g 10001 proxytool \
    && adduser -D -u 10001 -G proxytool proxytool
WORKDIR /app
COPY config.example.json with_proxy.py ./
COPY sdk/ sdk/
COPY web/ web/
RUN mkdir -p /app/data && chown proxytool:proxytool /app/data
USER proxytool
# The container console listens on every interface. Set NET_PROXY_ACCESS_TOKEN to
# choose the access token; when it is empty the console generates one and
# prints the access link in the container log.
ENV NET_PROXY_CONFIG=/app/data/config.json NET_PROXY_BIND=0.0.0.0 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
EXPOSE 8899
HEALTHCHECK --interval=10s --timeout=3s --start-period=3s \
    CMD python -c "import http.client; c=http.client.HTTPConnection('127.0.0.1',8899,timeout=2); c.request('GET','/api/health'); assert c.getresponse().status == 200"
ENTRYPOINT ["python", "web/server.py", "8899"]
