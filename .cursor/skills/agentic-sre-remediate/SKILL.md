---
name: agentic-sre-remediate
description: |
  Orchestrate host+CVE remediation for Agentic SRE labs: resolve Insights/AAP hosts,
  validate with fresh local evidence, plan idempotent fixes, gated git/AAP sync/JT,
  separate remediation vs verification, three verification verdicts, Lightspeed lag
  checks, and Markdown evidence reports. Use when: "/agentic-sre-remediate",
  "remediate CVE-X on host Y", host-scoped CVE patch with approval gates.
  Prefer over /remediation for single-host Agentic SRE workflows.
disable-model-invocation: false
---

# Agentic SRE Remediate

End-to-end **host + CVE** remediation orchestration for the Agentic SRE lab pattern.
Delegates to existing skills and MCP-backed workflows. Does **not** call destructive
actions without explicit, phase-specific human approval.

## Inputs (required)

| Input | Description |
|-------|-------------|
| `host` | Target hostname or FQDN (single host unless batch explicitly approved) |
| `cve` | CVE identifier (`CVE-YYYY-NNNNN`) |

Optional: advisory hint, maintenance window notes, repo path override.
**Do not** treat any lab hostname, CVE, RHSA, or kernel EVR as required defaults.
Lab examples live only in [references/06-lab-defaults.md](references/06-lab-defaults.md).

## Decision vocabulary

### Planning decision (before remediation execution)

| Decision | Meaning |
|----------|---------|
| `REMEDIATE` | Local evidence shows applicable, unfixed issue; proceed through gates |
| `NO_ACTION_REQUIRED` | Already remediated **or** demonstrably not applicable on this host |

`NO_ACTION_REQUIRED` is a **planning** outcome. It is **not** one of the three
post-execution verification verdicts.

### Post-execution verification verdicts (after read-only verify)

| Verdict | Meaning | AAP verify job |
|---------|---------|----------------|
| `REMEDIATED` | Local checks prove fix active | Prefer `successful` |
| `NOT_REMEDIATED` | Verify completed; fix missing/inactive | Prefer `successful` |
| `VERIFICATION_ERROR` | Evidence unreliable | Must `failed` |

## Safety (mandatory)

- Never remediate multiple hosts without explicit approval per target or an explicitly approved batch list.
- Never execute arbitrary generated shell without review.
- Never install packages or reboot before **Remediation execution** approval (reboot called out explicitly in that gate).
- Never expose credentials or tokens.
- Never weaken sudo, SELinux, firewall, or other controls to force success.
- Stop if local evidence conflicts with the proposed remediation.
- Keep remediation execution separate from verification (separate JT / launch / approval).
- Do not claim Lightspeed confirmation until vulnerability **evaluation** reflects post-remediation data (see [references/04-evidence-and-lightspeed.md](references/04-evidence-and-lightspeed.md)).
- Historical AAP jobs are context only — **never** proof of current host state.
- Prefer fresh read-only local evidence via AAP; **Probe approval** required before launching any probe job.

## Approval gates (separate; never combine)

Record each approval with UTC timestamp in the evidence artifact.

1. **Read-only probe execution**
2. **Remediation plan** (or accept `NO_ACTION_REQUIRED` and stop remediation path)
3. **Git commit/push**
4. **Remediation execution** (including any reboot if in plan)
5. **Post-remediation verification**
6. **Evidence report publication** (commit/push of report)

Exact prompts: [references/01-approval-gates.md](references/01-approval-gates.md).

### Approval reply vocabulary

| Gate | Accept replies | Abort |
|------|----------------|-------|
| Probe | `approve-probe` | `abort` |
| Plan | `approve-plan` or `accept-no-action` | `abort` |
| Git | `approve-git` | `abort` |
| Remediate (+ reboot if planned) | `approve-remediate` | `abort` |
| Verify | `approve-verify` | `abort` |
| Report publish | `approve-report` | `abort` |

## Skill map

Delegate; do not reinvent. See [references/05-skill-map.md](references/05-skill-map.md).

| Phase | Prefer |
|-------|--------|
| MCP health | `/mcp-lightspeed-validator`, `/mcp-aap-validator` |
| CVE validity / remediability | `/cve-validation` (+ optional `/cve-impact`) |
| Host / deployment context | `/system-context`, inventory find/list tools via skill rules |
| Playbook from Lightspeed | `/playbook-generator` when Remediations MCP available |
| AAP project sync | Bundled `/aap-project-sync` after approved push; require approved revision match |
| JT suitability | `/job-template-remediation-validator`; create via MCP or `/job-template-creator` |
| Launch / monitor jobs | `/playbook-executor` patterns (still respect **this** skill’s gates) |
| Lightspeed post-check | `/remediation-verifier` patterns + eval/upload timeline rules here |
| Session audit | `/execution-summary` |

**Skill-first:** Do not call Lightspeed/AAP MCP tools directly when a skill covers the step,
except where this skill explicitly requires inventory UUID / AAP host resolution and
job evidence collection already used by those skills.

## Workflow

Complete phases in order. **Do not start phase N+1 until phase N finishes** and any
required approval is recorded.

### Phase 0 — Accept inputs

1. Parse `host` and `cve`. If either missing, ask once and stop.
2. If multiple hosts requested, require explicit per-host or named-batch approval before continuing.
3. Present high-level phase list; do **not** launch probes yet.

### Phase 1 — Validate MCP

1. Run `/mcp-lightspeed-validator` then `/mcp-aap-validator` (skip only if already PASSED this session).
2. On FAILED: stop with setup guidance. On PARTIAL: warn and ask whether to continue.

### Phase 2 — Resolve hosts

1. Resolve Insights inventory UUID for `host` (FQDN preferred).
2. Resolve matching AAP inventory host (same FQDN / inventory hostname).
3. Record: Insights UUID, AAP inventory id, AAP host id/name, org if present.
4. If either side missing: stop — do not invent UUIDs.

### Phase 3 — CVE and advisory facts (Lightspeed)

1. Run `/cve-validation` for `cve`.
2. Collect severity/CVSS when available, advisories list, remediability signals.
3. Confirm host appears affected **or** note Lightspeed says not affected (local probe still required before `NO_ACTION_REQUIRED` unless validation proves CVE invalid).

### Phase 4 — Fresh local applicability (read-only)

1. Present what the probe will check (packages/advisory/`uname`/services as relevant). **No changes.**
2. Obtain **Probe approval** (gate 1). If denied → stop.
3. Launch **read-only** AAP evidence collection limited to the target host only
   (prefer existing verification / privilege-check style playbooks parameterized for this CVE,
   or a minimal read-only probe JT). Never install/reboot in this phase.
4. Parse current local package/advisory/service evidence.
5. Historical jobs may be cited as background only.

### Phase 5 — Planning decision

Using **local** evidence + Lightspeed context:

1. If already fixed or not applicable → planning decision `NO_ACTION_REQUIRED`.
   - Still may generate a short evidence note; skip remediation/git/execute.
   - Optionally offer verification-only later (separate approval).
2. Else → planning decision `REMEDIATE`.
3. Classify remediation (package EVR, service restart, config, kernel+reboot, other).
   See [references/03-remediation-classes.md](references/03-remediation-classes.md).
4. Detect: privileges (`become`), dependencies, reboot need, maintenance window questions.
5. Present plan via [references/02-plan-template.md](references/02-plan-template.md).
6. Obtain **Plan approval** (gate 2). If `NO_ACTION_REQUIRED` accepted → jump to Phase 11 (report) as applicable.

### Phase 6 — Playbook generate or reuse

1. If Remediations MCP available: try `/playbook-generator`; return YAML **as-is** first.
2. If unavailable or unsuitable: reuse repo playbook **or** generate a scoped playbook draft.
3. **Mandatory review before any later execution approval** (especially when not from Lightspeed AS-IS):
   - Applicability to this CVE/host
   - Exact packages / versions or services
   - Advisory alignment
   - Idempotency
   - Host scope (`limit` / `expected_hostname` / asserts) — single approved host only
4. Stop if scope could touch other hosts or weakens security controls.

### Phase 7 — Git commit/push

1. Show paths and diff summary.
2. Obtain **Git approval** (gate 3).
3. Commit/push only after approval. Never push secrets. Record the complete Git commit SHA that was actually pushed.
4. Invoke the **bundled** `/aap-project-sync` skill (`.cursor/skills/aap-project-sync/SKILL.md`) for the configured Project, passing the approved full commit SHA and relative playbook path. Its shared helper is `scripts/aap_project_sync.py` with `--expected-revision`; then verify playbook visibility through AAP MCP.
5. If the Project Update fails, the AAP `scm_revision` differs from the approved commit, or the playbook cannot be verified: **stop**. Never continue to JT creation/execution on unverified content.

### Phase 8 — Job Template

1. Find existing JT for this playbook + inventory, or create via AAP MCP / `/job-template-creator`.
2. Enforce **limit = target host FQDN** (or exact inventory hostname).
3. Validate with `/job-template-remediation-validator` when remediate JT; verification JT must be read-only and separate.
4. Record JT ids/names.

### Phase 9 — Remediation execution

1. Preview tasks, packages, reboot yes/no.
2. Obtain **Remediation execution approval** (gate 4). Reboot must be called out in the prompt if planned.
3. Launch via AAP; monitor to completion.
4. Collect Job ID, status, timestamps, host summary, stdout evidence (before/after packages if present).
5. On unexpected package set or verification-error style failures: stop and report; do not auto-retry destructive steps.

### Phase 10 — Post-remediation verification (separate)

1. Obtain **Verification approval** (gate 5) — never auto-chain from remediation success.
2. Launch read-only verification JT limited to the same host.
3. Require structured verdict: `REMEDIATED` | `NOT_REMEDIATED` | `VERIFICATION_ERROR`.
4. Prefer job success for `REMEDIATED` / `NOT_REMEDIATED`; fail job only on `VERIFICATION_ERROR`.

### Phase 11 — Lightspeed comparison

1. Re-query inventory check-in/upload and CVE affected status for the host.
2. Compare `last_evaluation` (and rules evaluation if present) to remediation job finish and latest upload.
3. Classify: evaluation lag vs missing upload vs package mismatch vs confirmed clear.
4. Claim “Lightspeed confirmed” **only** when evaluation post-dates remediation **and** host is no longer affected (or explicitly marked remediated by API).

### Phase 12 — Evidence report

1. Write Markdown under `reports/` using
   `scripts/generate-remediation-evidence-report.py` (or equivalent structured update).
2. Include: host details, Insights UUID, AAP host ids, CVE, advisory, package versions,
   all job IDs, all approval timestamps, execution results, planning decision,
   verification verdict, Lightspeed timestamps, final security conclusion.
3. Obtain **Report publication approval** (gate 6) before commit/push of the report.

## Idempotency and scope validation

Before remediation launch, confirm playbook:

- Uses package `state: present` / version pins or equivalent idempotent modules
- Does not perform blanket `dnf upgrade` unless explicitly approved in plan
- Restricts to approved host (limit + in-play hostname asserts when used)
- Does not disable security subsystems

## Outputs

- Planning decision: `REMEDIATE` | `NO_ACTION_REQUIRED`
- If executed: remediation Job ID + verification Job ID + verification verdict
- Lightspeed lag/confirmation assessment
- Path to Markdown evidence report

## Example invocation

```text
/agentic-sre-remediate host=<fqdn> cve=CVE-YYYY-NNNNN
```

Natural language: “Remediate CVE-YYYY-NNNNN on host &lt;fqdn&gt; using agentic-sre-remediate.”

## References

| File | Purpose |
|------|---------|
| [01-approval-gates.md](references/01-approval-gates.md) | Exact HITL prompts |
| [02-plan-template.md](references/02-plan-template.md) | Plan presentation format |
| [03-remediation-classes.md](references/03-remediation-classes.md) | Package/service/kernel/no-op |
| [04-evidence-and-lightspeed.md](references/04-evidence-and-lightspeed.md) | Verdicts + eval/upload rules |
| [05-skill-map.md](references/05-skill-map.md) | Delegation details |
| [06-lab-defaults.md](references/06-lab-defaults.md) | Optional lab examples only |
