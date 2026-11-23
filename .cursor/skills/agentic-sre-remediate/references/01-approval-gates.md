# Approval gates (verbatim prompts)

Each gate is separate. Do not bundle approvals. Record: gate name, user reply, UTC time.

## Gate 1 — Read-only probe

```
PROBE APPROVAL REQUIRED (read-only)

Host: <host>
CVE: <cve>
Probe will: collect local package/advisory/kernel/service evidence via AAP.
Probe will NOT: install packages, remove packages, change config, or reboot.

Reply: approve-probe | abort
```

## Gate 2 — Remediation plan

```
PLAN APPROVAL REQUIRED

Planning decision: REMEDIATE | NO_ACTION_REQUIRED
Host: <host>
CVE: <cve>
Advisory: <advisory or none>
Actions: <packages/services/config>
Reboot required: yes | no
Privileges: become=<true|false>

If NO_ACTION_REQUIRED: reply accept-no-action | abort
If REMEDIATE: reply approve-plan | abort
```

## Gate 3 — Git commit/push

```
GIT APPROVAL REQUIRED

Repo: <path>
Branch: <branch>
Files: <list>
Summary: <1-2 sentences>

Reply: approve-git | abort
(Do not push secrets. Sync AAP only after successful push.)
```

## Gate 4 — Remediation execution

```
REMEDIATION EXECUTION APPROVAL REQUIRED

Job Template: <name> (id=<id>)
Limit: <exact host>
Playbook: <path>
Changes: <packages/services>
Reboot: yes | no   ← must match approved plan; if yes, this approval includes reboot
Snapshot / rollback: <operator acknowledgement if required by plan>

Reply: approve-remediate | abort
```

## Gate 5 — Post-remediation verification

```
VERIFICATION APPROVAL REQUIRED (read-only; separate from remediation)

Verification Job Template: <name> (id=<id>)
Limit: <exact host>
Expected local verdicts: REMEDIATED | NOT_REMEDIATED | VERIFICATION_ERROR

Reply: approve-verify | abort
```

## Gate 6 — Evidence report publication

```
REPORT PUBLICATION APPROVAL REQUIRED

Report path: <path>
Will commit/push: yes (report only unless otherwise stated)

Reply: approve-report | abort
```
