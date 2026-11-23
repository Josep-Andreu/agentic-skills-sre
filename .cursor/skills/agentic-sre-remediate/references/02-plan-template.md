# Remediation plan template

Present after local probe + CVE facts. Use this structure exactly.

## Summary

1–2 sentences: what will change on which host and why (or why no action).

## Decision

| Field | Value |
|------|--------|
| Planning decision | `REMEDIATE` \| `NO_ACTION_REQUIRED` |
| Host (FQDN) | |
| AAP host id / name | |
| Insights UUID | |
| CVE | |
| Advisory | |
| Lightspeed still lists host? | yes \| no \| unknown |
| Local evidence source | probe Job ID / timestamp |

## Technical plan

| Field | Value |
|------|--------|
| Remediation class | package \| service \| config \| kernel+reboot \| other \| none |
| Packages / versions (NEVRA or EVR) | |
| Services affected | |
| Reboot required | yes \| no |
| become / root required | yes \| no |
| Idempotent? | yes \| notes |
| Host scope enforcement | JT limit + playbook asserts |
| Maintenance window | stated \| not stated |

## Checklist

1. MCP validators — done / pending
2. Host resolution (Insights + AAP) — done / pending
3. CVE validation — done / pending
4. Fresh local probe — done / pending (Job …)
5. Plan approval — **waiting**
6. Playbook review — pending
7. Git + `/aap-project-sync` — pending
8. JT limit check — pending
9. Remediation launch — pending
10. Verification launch — pending
11. Lightspeed eval/upload compare — pending
12. Evidence report — pending

## Confirm

Use Gate 2 prompt from `01-approval-gates.md`.
