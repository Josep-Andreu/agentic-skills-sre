# Skill and tool delegation map

Orchestrator: `/agentic-sre-remediate`. Prefer these skills over ad-hoc MCP.

| Need | Skill / action |
|------|----------------|
| Lightspeed MCP health | `/mcp-lightspeed-validator` |
| AAP MCP health | `/mcp-aap-validator` |
| CVE format / remediability | `/cve-validation` |
| Risk / fleet impact (optional) | `/cve-impact` |
| Affected systems / RHEL context | `/system-context` |
| Lightspeed vuln playbook YAML | `/playbook-generator` (Remediations MCP) |
| If Remediations MCP down | Reuse or author playbook in git repo; mandatory human review of applicability, packages, advisory, idempotency, host scope |
| Commit/push playbooks | Git with Gate 3 approval only |
| AAP project SCM sync | `/aap-project-sync` |
| Create JT guidance | `/job-template-creator` or AAP MCP `job_templates_create` when available |
| JT ready for remediate | `/job-template-remediation-validator` |
| Launch/monitor jobs | `/playbook-executor` patterns **plus** this skill’s gates (probe / remediate / verify are separate) |
| Lightspeed post status | `/remediation-verifier` patterns + eval/upload rules in `04-evidence-and-lightspeed.md` |
| Session audit | `/execution-summary` |

## vs `/remediation`

| | `/remediation` | `/agentic-sre-remediate` |
|--|----------------|-------------------------|
| Scope | Generic Red Hat pack | Host+CVE Agentic SRE lab path |
| Local probe gate | Not primary | Required fresh AAP probe (approved) |
| Git / sync gates | Via executor Git Flow | Explicit Gate 3 + `/aap-project-sync` |
| Verify verdicts | Varied | `REMEDIATED` / `NOT_REMEDIATED` / `VERIFICATION_ERROR` |
| Planning | Remediate-oriented | Includes `NO_ACTION_REQUIRED` |

For “remediate &lt;CVE&gt; on &lt;host&gt;” in Agentic SRE, prefer `/agentic-sre-remediate`.
