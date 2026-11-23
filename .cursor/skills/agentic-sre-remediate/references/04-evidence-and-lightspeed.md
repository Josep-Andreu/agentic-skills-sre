# Evidence, verdicts, and Lightspeed lag

## Planning decision vs verification verdicts

| Kind | Values | When |
|------|--------|------|
| Planning decision | `REMEDIATE`, `NO_ACTION_REQUIRED` | After local probe, before remediation |
| Verification verdict | `REMEDIATED`, `NOT_REMEDIATED`, `VERIFICATION_ERROR` | After read-only post-remediation verify |

Do not conflate `NO_ACTION_REQUIRED` with `REMEDIATED`.
`NO_ACTION_REQUIRED` means no remediation run is warranted now.
`REMEDIATED` means a verification play proved the fix on the host after (or instead of) a remediation run when verification was approved.

## Fresh local evidence

- Prefer a newly approved read-only AAP probe (Gate 1).
- Historical AAP jobs: context only; never sole proof of current state.
- Record probe Job ID, started/finished UTC, packages, advisory pending yes/no, running kernel/service facts as applicable.

## Structured evidence fields (minimum)

- `generated_utc`
- `hostname`, `insights_uuid`, `aap_inventory_id`, `aap_host_id`
- `cve`, `advisory`
- `planning_decision`
- `approvals[]`: `{gate, decision, utc}`
- `probe_job_id`, `remediation_job_id`, `verification_job_id`
- Package versions before/after (or current if no remediate)
- `security_verdict` (verification) or `n/a` if not run
- Lightspeed: `last_check_in`, `last_upload`, `last_evaluation`, still_affected yes/no
- Final conclusion string

Use repo script `scripts/generate-remediation-evidence-report.py` when available.

## Lightspeed confirmation rules

Compare timestamps:

1. Remediation job `finished` (if any)
2. Inventory / vuln `last_upload` or host `last_check_in`
3. Vuln `last_evaluation` (and `rules_evaluation` if present)

| Situation | Classification |
|-----------|----------------|
| Upload/check-in after remediate; evaluation still before remediate; still listed | Stale vulnerability evaluation |
| No upload/check-in after remediate | Missing / pending reporting |
| Inventory packages still vulnerable EVRs after claimed fix | Possible genuine discrepancy — stop and investigate |
| Evaluation after remediate AND host not on affected list | Lightspeed confirmed clear |

**Never** claim Lightspeed confirmation until evaluation reflects post-remediation data **and** affected status clears (or API explicitly marks remediated).
