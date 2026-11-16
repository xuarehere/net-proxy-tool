# Contributing

Start from the [quick start](QUICKSTART_EN.md) with an empty configuration. A useful bug report states what was downloaded (release archive, source ZIP, Git checkout or wheel), the OS and CPU architecture, the launcher or command used and the first error. Include a short redacted log excerpt if available.

## Develop and test

The Web service, CLI and SDK use Python's standard library. Keep runtime changes compatible with the supported Python versions in `pyproject.toml`. Use a disposable configuration path for manual checks. From the repository root on Windows PowerShell:

```powershell
$env:NET_PROXY_CONFIG = Join-Path ([System.IO.Path]::GetTempPath()) ("npt-" + [guid]::NewGuid() + "/config.json")
python launcher.py --no-browser
python launcher.py --stop
python -m unittest discover -s test
```

On macOS or Linux:

```bash
export NET_PROXY_CONFIG="$(mktemp -d)/config.json"
python3 launcher.py --no-browser
python3 launcher.py --stop
python3 -m unittest discover -s test
```

When changing packaging, build and install a wheel in a clean virtual environment, change to a directory outside the checkout and exercise both entry points. When changing the Web console, test a clean first run with an HTTP proxy and inspect the actual request on the proxy side. Verify failure behavior with an unused port. For remote operations, use a disposable node and compare its files before and after switching.

## Documentation and artwork

Keep the [Chinese](README.md) and [English](README_EN.md) download tables and quick starts in sync with the release asset names and command output. Both architecture diagrams are generated from [one Python source](docs/render_architecture.py). After editing its labels or layout, regenerate both assets.

```console
python docs/render_architecture.py
```

Capture screenshots from a running console with an isolated, empty configuration. Mention the environment and any test skips in the pull request. Review the diff for credentials, local paths and internal infrastructure before submitting.

## 中文说明

请在独立配置中复现问题，写明版本、系统、架构、下载包或源码入口及首条错误。提交前运行测试；涉及打包时验证干净环境，涉及远程开关时验证恢复后的目标文件。变更下载方式或首用界面时同步更新中英文指南与截图。
