# Security policy

## What the console can do

The console runs commands with the privileges of its operating-system account. A node switch can update files in another account or container over SSH. Run the console as a regular user and give each remote login only the permissions its workload needs. A child process inherits the user's file and network access. Proxy environment variables only affect applications that honor them.

The desktop launcher binds to loopback. Compose publishes the container port on the host's loopback interface. For a remote machine, use SSH port forwarding to reach the console. Keep the management port off public networks. Requests from untrusted browsers are checked against the allowed host and origin. Other software running under your account is inside the trust boundary.

## Credentials and backups

- Protect `config.json` and the adjacent `data/` directory with your account's filesystem permissions. The saved configuration can contain SSH login credentials. JSON API responses omit credential fields. `data/instance.json` includes the shutdown token.
- Prefer SSH keys. The Windows control host uses OpenSSH key authentication. On a POSIX control host, password-based provisioning may install the control user's public key in the target account's `authorized_keys`. Verify the target host key independently before first contact.
- Back up a managed node's tool and shell settings before its first persistent switch. When running as root, the remote operation can affect system-wide tool configuration.
- Share sanitized examples and the minimum diagnostic excerpt needed. Remove tokens, passwords, shutdown state, usernames and internal hostnames from screenshots and logs.

## Report a vulnerability

Use the repository's [Security page](https://github.com/xuarehere/net-proxy-tool/security) for private reporting when enabled, or contact the maintainer privately. Include the release, platform, affected entry point and a minimal reproduction using disposable credentials. Public bug reports should avoid exploitation details and private topology.

## 中文说明

控制台可以以当前账号的权限执行命令。远程节点的开关可以修改目标工具或 shell 配置，root 账号还能修改系统级设置。控制台应由普通用户在回环地址运行；从其他机器访问时使用 SSH 端口转发。配置可能含 SSH 密码，`data/instance.json` 含停机令牌，均应限制读取权限。Windows 控制端使用 OpenSSH 密钥认证。报告漏洞时请使用私密渠道，附版本、平台以及使用临时凭据的最小复现步骤。
