# Kiro 与编程代理指南

本项目由 AI 编程代理参与开发，代理的工作方式是仓库的一部分，而不是私下的习惯。下面的内容说明这些材料放在哪里，便于评审者跟进工作，也便于贡献者接手。

[English](kiro_en.md) · [快速上手](../QUICKSTART.md) · [运维与排障](operations.md)

## 仓库里有什么

| 路径 | 内容 |
| --- | --- |
| `.kiro/specs/<feature>/` | 一个特性的需求、设计与任务清单 |
| `.kiro/steering/` | 对每次改动都生效的长期规则 |
| `.kiro/hooks/` | 保护并检查工作的文件钩子 |
| `.kiro/agents/` | 面向出网排障的自定义代理 |
| `kiro-power/` | 代理在本仓库需要的检查与命令 |
| `tools/kiro/` | 钩子、power 与发布流程实际运行的脚本 |
| `test/test_prop_*.py` | 每份规格所命名的 property 测试 |
| `docs/kiro/mcp.json` | 供代理登记 MCP 服务器的配置文件 |

## 规格

每个特性都有自己的目录，包含三份文件：

- `requirements.md` 用 EARS 形式陈述需求（“WHEN … THE Console SHALL …”）。
- `design.md` 描述接口、错误处理、决策与正确性性质（Correctness Properties）。
- `tasks.md` 列出工作项并标注完成情况。

每次改动都遵循同一顺序：先写规格，再写会失败的测试，然后实现，随后跑完整测试，最后做一次提交。property 测试的 docstring 里写明性质编号与它验证的需求，读者可以从需求一路走到证明它的测试。

## steering 规则

steering 文件保存不属于某一个特性的规则：

| 文件 | 生效范围 | 规则 |
| --- | --- | --- |
| `product.md` | 始终 | 工具承诺什么、不承诺什么 |
| `tech.md` | 始终 | Python 3.8、仅标准库、打包白名单 |
| `structure.md` | 始终 | 各类文件放在哪里 |
| `zero-pollution.md` | 始终 | 代理只进入子进程、账号或容器，不多一分 |
| `security.md` | 运行时代码 | 输入校验、脱敏、超时、进程树 |
| `testing.md` | 测试 | 临时配置、空闲端口、不含凭据的 fixture |
| `i18n.md` | 控制台 | 语言键与回退规则 |
| `docs-style.md` | 文档 | 中英文成对文件保持同步 |
| `release.md` | 发布 | 发布流程与需要批准的步骤 |
| `field-validation.md` | 现场检查 | 默认只读，真实数据只留在 `scratch/` |

## hooks

`.kiro/hooks/` 中的钩子在代理事件上运行，背后是 `tools/kiro/` 里的脚本：

| 钩子 | 触发时机 | 作用 |
| --- | --- | --- |
| `shell-guard` | 执行命令前 | 拦截会打印 remote URL、令牌或控制台配置的命令，以及强制 push |
| `file-guard` | 修改文件前 | 拦截对控制台配置的读写，以及会让运行时代码引入第三方 import 的写入 |
| `stdlib-only` | 保存文件后 | 报告标准库以外的运行时 import |
| `related-tests` | 一轮结束时 | 运行与改动文件相关的测试模块 |
| `task-verify` | 任务完成后 | 运行完整测试 |
| `session-brief` | 会话开始 | 复述分支、未提交工作与长期规则 |
| `docs-pair` | 保存文档后 | 提醒代理同步另一语言版本 |

## MCP 服务器

`net_proxy_mcp.py` 通过 Model Context Protocol 提供控制台的诊断能力，编程代理读到的是与操作者相同的状态：

| 工具 | 作用 | 自动批准 |
| --- | --- | --- |
| `list_gateways` | 列出已配置的网关 | 是 |
| `check_gateway` | 通过一个网关发送一次请求 | 是 |
| `check_gateway_targets` | 探测已配置的诊断站点 | 是 |
| `list_nodes` | 列出节点及其实际生效的代理 | 是 |
| `test_node` | 对一个节点执行控制台的双路请求 | 否 |
| `run_with_proxy` | 带代理变量运行一条命令 | 否 |

服务器不会写入配置，也不会切换节点。`run_with_proxy` 不经 shell 启动一个程序，代理变量只存在于子进程中，运行时间与输出都有上限，被取消或超时时会结束整个进程树。加上 `inspect` 后，命令会经过本机观测网关，并报告它访问过哪些主机。

登记方式：把 `docs/kiro/mcp.json` 复制到代理自己的设置目录。仓库不保存该文件，因为它属于具体机器。

## power 与自定义代理

`kiro-power/` 收纳代理在本仓库需要的命令：会话简报、标准库检查、密钥扫描、发布一致性检查、相关测试与演示脚本。它们都是只读的。

`.kiro/agents/egress-diagnostician.md` 是面向这类问题的自定义代理：请求为什么没有经代理出去。它会指明请求停在哪一段，并说明哪些环节尚未核验。

## 检查命令

```console
python -X utf8 tools/kiro/check_stdlib.py --all
python -X utf8 tools/kiro/scan_secrets.py --staged
python -X utf8 tools/kiro/check_release_consistency.py
python -X utf8 -m unittest discover -s test
```

前三条不需要网络。测试套件需要临时配置与空闲端口，不使用 8899，也不访问真实目标。
