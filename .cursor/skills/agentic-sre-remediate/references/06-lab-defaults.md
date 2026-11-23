# Lab defaults (examples only — not required inputs)

These values document a common Agentic SRE lab layout.
**The skill must accept arbitrary `host` + `cve`.** Do not hardcode the examples below as required parameters.

| Item | Example lab value |
|------|-------------------|
| Git repository | `/path/to/agentic-sre` |
| AAP Controller API | Lab HTTPS Controller URL (not MCP gateway port) |
| AAP project name / id | `Agentic-SRE-Lab` (example id may vary) |
| AAP inventory name | `Agentic-SRE-Lab` |
| Credentials file (token) | `~/.config/agentic-sre/credentials` (`AAP_API_TOKEN`) — never print |
| Sync helper | `scripts/aap_project_sync.py` |
| Evidence script | `scripts/generate-remediation-evidence-report.py` |
| Example verify playbook path | `playbooks/verify-cve-2026-114406.yml` (documentation example only) |
| Example remediate playbook path pattern | `playbooks/remediate-<cve>.yml` |

When invoking the skill, always pass the real target host and CVE explicitly.
