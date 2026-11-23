# Security and responsible disclosure

This repository is a demonstration of approval-gated remediation. It is not a production change-management system or a security advisory service.

- Never submit credentials, real inventory, customer reports, remote Controller URLs, production FQDNs, private repository addresses or private keys to an issue or pull request.
- Scope automation to an explicit approved host. Do not enable write-capable MCP tools without externally enforced access controls and independent human approval.
- Do not publish actual remediation output by default; `reports/`, `demo-reports/` and controller configuration are ignored.
- Sample versions, CVE IDs and RHSA IDs are **technical examples only** and must be independently checked before deployment.
- Before publishing changes, run `python3 scripts/check-publication.py` and inspect `git diff --cached`.
- If a credential was ever uploaded to a remote repository, rotate it. Deleting the file in a later commit does not remove it from Git history.

Contact the maintainers privately for vulnerability reports. Do not paste secrets into public GitHub issues.
