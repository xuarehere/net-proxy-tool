# Security policy

## What the console can do

The console runs commands with the privileges of its operating-system account. A node switch can update files in another account or container over SSH. Run the console as a regular user and give each remote login only the permissions its workload needs. A child process inherits the user's file and network access. Proxy environment variables only affect applications that honor them.

The desktop launcher binds to loopback. Compose publishes the container port on the host's loopback interface. For a remote machine, use SSH port forwarding to reach the console. Keep the management port off public networks. Requests from untrusted browsers are checked against the allowed host and origin. The management API has no per-user login. Every local account or process that can connect to the loopback port can operate the console with the server account's privileges. On shared servers, isolate the listener in a dedicated network namespace or VM and restrict access to trusted operators. An SSH tunnel protects remote transport; it does not exclude other local clients.

The console request runner accepts HTTP(S) probes. Run other application commands from a local terminal using the CLI. A remote test runs in the selected account or container. Review the node and gateway together before enabling a persistent configuration.

## Credentials and backups

- Protect `config.json` and the adjacent `data/` directory with your account's filesystem permissions. The saved configuration can contain SSH login credentials. JSON API responses omit credential fields. `data/instance.json` includes the shutdown token.
- Use the SSH identity configured for that node. For password authentication, verify the server fingerprint and trust the matching host and port in the control account’s OpenSSH known_hosts before testing. Each saved password belongs to its configured destination and account. The normal provisioning workflow leaves authorized_keys under operator control.
- Back up a managed node's tool and shell settings before its first persistent switch. When running as root, the remote operation can affect system-wide tool configuration.
- Share sanitized examples and the minimum diagnostic excerpt needed. Remove tokens, passwords, shutdown state, usernames and internal hostnames from screenshots and logs.

## Report a vulnerability

Use the repository's [Security page](https://github.com/xuarehere/net-proxy-tool/security) for private reporting when enabled, or contact the maintainer privately. Include the release, platform, affected entry point and a minimal reproduction using disposable credentials. Public bug reports should avoid exploitation details and private topology.

## 中文说明

控制台可以以当前账号的权限执行命令。远程节点的开关可以修改目标工具或 shell 配置，root 账号还能修改系统级设置。控制台应由普通用户在回环地址运行。管理接口没有逐用户登录，能访问该回环端口的本机账号或程序都可以操作控制台。共享服务器应通过独立网络命名空间或虚拟机限制访问，只允许受信任的操作人员连接。从其他机器访问时使用 SSH 端口转发，本机端口仍需隔离。配置可能含 SSH 密码，`data/instance.json` 含停机令牌，均应限制读取权限。密码认证使用节点单独配置的登录身份。先核对服务器指纹，并在运行控制台的账号下信任该 SSH 主机及端口。报告漏洞时请使用私密渠道，附版本、平台以及使用临时凭据的最小复现步骤。
