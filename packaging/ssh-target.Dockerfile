# Disposable SSH target used only by packaging/test_compose.py.
FROM python:3.12-alpine
RUN apk add --no-cache openssh-server git \
    && adduser -D tester && passwd -d tester \
    && mkdir -p /run/sshd /home/tester/.ssh \
    && chmod 700 /home/tester/.ssh && chown -R tester:tester /home/tester
CMD ["sh", "-ec", "ssh-keygen -A >/dev/null; exec /usr/sbin/sshd -D -e -o PasswordAuthentication=no -o PermitRootLogin=no"]
