# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| < 1.3.0 | :x:                |

## Security Architecture & Best Practices

1. **Configuration Hygiene**:
   - `config.json` contains your network topology, hosts, and SSH credentials. It is untracked by Git via `.gitignore`.
   - Never commit `config.json` or private credentials to public repositories.
   - Use `config.example.json` with RFC 1918 addresses (`192.168.1.x`) for public sharing.

2. **SSH & Execution Security**:
   - Remote execution relies on native SSH key authentication whenever possible.
   - When password authentication is used for bootstrap, passwords are fed via ephemeral standard input/ASKPASS in memory and never written to permanent disk logs.

## Reporting a Vulnerability

If you discover a security vulnerability in `net-proxy-tool`:
- Please report it responsibly via GitHub Private Vulnerability Reporting or contact the maintainer directly.
- Please do not open public issues for sensitive security vulnerabilities until a patch is available.
- We will acknowledge receipt within 48 hours and work on a prompt remediation release.
