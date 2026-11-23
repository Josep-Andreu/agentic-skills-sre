#!/usr/bin/env python3
"""Generate a Markdown remediation evidence report (no secrets, no API calls).

Separates planning decisions, AAP execution status, verification verdicts, and
Lightspeed lag assessment. Fill fields via JSON produced after MCP / job output.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TEMPLATE = """# Remediation evidence report

| Field | Value |
|------|--------|
| Generated (UTC) | {generated_utc} |
| Host | `{hostname}` |
| Insights inventory UUID | `{insights_uuid}` |
| AAP inventory id | `{aap_inventory_id}` |
| AAP host id | `{aap_host_id}` |
| CVE | `{cve}` |
| Advisory | `{advisory}` |
| Planning decision | `{planning_decision}` |
| Probe AAP Job ID | `{probe_job_id}` |
| Remediation AAP Job ID | `{remediation_job_id}` |
| Verification AAP Job ID | `{verification_job_id}` |

## Approvals

{approvals_table}

## Execution status vs security verdict

| Field | Value | Notes |
|------|--------|-------|
| Planning decision | `{planning_decision}` | `REMEDIATE` / `NO_ACTION_REQUIRED` (pre-execution) |
| Verification play execution | `{execution_status}` | `completed` / `verification_error` / `n/a` |
| Security verdict | `{security_verdict}` | `REMEDIATED` / `NOT_REMEDIATED` / `VERIFICATION_ERROR` / `n/a` |
| AAP verification job status | `{verification_job_status}` | Fail only for `VERIFICATION_ERROR` |
| Verdict reasons | {verdict_reasons} | |

## Status matrix (three layers)

| Layer | Status | Notes |
|------|--------|-------|
| Historical AAP remediation | {historical_remediation_status} | {historical_remediation_notes} |
| Current local host (this verify) | {local_verified_status} | {local_verified_notes} |
| Lightspeed vulnerability data | {lightspeed_confirmed_status} | {lightspeed_confirmed_notes} |
| Lightspeed data stale / not yet updated | {lightspeed_stale_status} | {lightspeed_stale_notes} |

## Lightspeed timestamps

| Field | Value |
|------|--------|
| last_check_in | `{lightspeed_last_check_in}` |
| last_upload | `{lightspeed_last_upload}` |
| last_evaluation | `{lightspeed_last_evaluation}` |
| still_affected | `{lightspeed_still_affected}` |

## Package / advisory evidence

| Item | Before | After / current |
|------|--------|-----------------|
| Running kernel (if applicable) | `{previous_kernel}` | `{current_kernel}` |
| Target fixed kernel / EVR | — | `{target_kernel}` / `{target_kernel_evr}` |
| Fixed RPMs present | — | `{fixed_rpms_present}` |
| Running kernel OK | — | `{kernel_running_ok}` |

### Installed packages (verification)
```
{installed_rpms}
```

### Per-package EVR evaluation
```
{package_evr_details}
```

### DNF advisory updates listing (`{advisory}`)
```
{advisory_listing}
```

| Item | Value |
|------|--------|
| Advisory still listed as updates | `{advisory_still_listed}` |

### Reboot
| Item | Value |
|------|--------|
| Remediation reboot performed | {reboot_performed} |
| Reboot still required | {reboot_still_required} |

## AAP job evidence

| Field | Probe | Remediation | Verification |
|------|-------|-------------|--------------|
| Job ID | {probe_job_id} | {remediation_job_id} | {verification_job_id} |
| Status | {probe_job_status} | {remediation_job_status} | {verification_job_status} |
| Started | {probe_started} | {remediation_started} | {verification_started} |
| Finished | {probe_finished} | {remediation_finished} | {verification_finished} |
| Counts | {probe_counts} | {remediation_counts} | {verification_counts} |

## Unresolved issues

{unresolved_issues}

## Reuse

```yaml
expected_hostname: "{hostname}"
target_cve: "{cve}"
target_advisory: "{advisory}"
target_kernel_release: "{target_kernel}"
target_kernel_evr: "{target_kernel_evr}"
previous_kernel_release: "{previous_kernel}"
```
"""


def _approvals_table(approvals) -> str:
    if not approvals:
        return "| Gate | Decision | UTC |\n|------|----------|-----|\n| (none recorded) | | |"
    if isinstance(approvals, str):
        return approvals
    lines = ["| Gate | Decision | UTC |", "|------|----------|-----|"]
    for row in approvals:
        if isinstance(row, dict):
            lines.append(
                f"| {row.get('gate', '')} | {row.get('decision', '')} | {row.get('utc', '')} |"
            )
        else:
            lines.append(f"| {row} | | |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, help="JSON object with report fields")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data: dict = {}
    if args.json:
        data = json.loads(args.json.read_text(encoding="utf-8"))

    defaults = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname": "<hostname>",
        "insights_uuid": "<uuid>",
        "aap_inventory_id": "n/a",
        "aap_host_id": "n/a",
        "cve": "<CVE-YYYY-NNNNN>",
        "advisory": "n/a",
        "planning_decision": "pending",
        "probe_job_id": "n/a",
        "remediation_job_id": "n/a",
        "verification_job_id": "n/a",
        "approvals_table": _approvals_table(None),
        "execution_status": "n/a",
        "security_verdict": "n/a",
        "verdict_reasons": "n/a",
        "historical_remediation_status": "n/a",
        "historical_remediation_notes": "",
        "local_verified_status": "n/a",
        "local_verified_notes": "",
        "lightspeed_confirmed_status": "n/a",
        "lightspeed_confirmed_notes": "",
        "lightspeed_stale_status": "unknown",
        "lightspeed_stale_notes": "",
        "lightspeed_last_check_in": "n/a",
        "lightspeed_last_upload": "n/a",
        "lightspeed_last_evaluation": "n/a",
        "lightspeed_still_affected": "n/a",
        "previous_kernel": "n/a",
        "current_kernel": "n/a",
        "target_kernel": "n/a",
        "target_kernel_evr": "n/a",
        "fixed_rpms_present": "n/a",
        "kernel_running_ok": "n/a",
        "installed_rpms": "(pending)",
        "package_evr_details": "(pending)",
        "advisory_listing": "(pending)",
        "advisory_still_listed": "n/a",
        "reboot_performed": "n/a",
        "reboot_still_required": "n/a",
        "probe_job_status": "n/a",
        "remediation_job_status": "n/a",
        "verification_job_status": "n/a",
        "probe_started": "n/a",
        "probe_finished": "n/a",
        "remediation_started": "n/a",
        "remediation_finished": "n/a",
        "verification_started": "n/a",
        "verification_finished": "n/a",
        "probe_counts": "n/a",
        "remediation_counts": "n/a",
        "verification_counts": "n/a",
        "unresolved_issues": "- None recorded",
    }

    merged = dict(defaults)
    for k, v in data.items():
        if v is None:
            continue
        if k == "approvals":
            merged["approvals_table"] = _approvals_table(v)
        else:
            merged[k] = v

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(TEMPLATE.format(**merged), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
