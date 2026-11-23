---
name: aap-project-sync
description: |
  After an explicitly approved Git push, synchronize an Ansible Automation Platform
  SCM Project, wait for a successful Project Update, compare the retrieved SCM
  revision to the approved Git commit, and confirm the intended playbook is
  available before a remediation Job Template can execute it.
disable-model-invocation: false
---

# AAP Project Sync

Synchronize a configured AAP Controller Project **after** a Git commit and push
approved by the operator. This skill is called by `/agentic-sre-remediate` in
Phase 7. It is **not** a remediation/execution skill and never starts a Job
Template, installs packages, or triggers a reboot.

## Requirements

- An accessible AAP Controller with an SCM-backed Project, and an API token
  authorized to read and update that Project.
- The containing `agentic-skills-sre` repository, including its shared helper
  `scripts/aap_project_sync.py`. This skill intentionally does **not** duplicate
  the Python script.
- Python 3 and a correctly configured AAP Controller URL, for example
  `https://controller.example.org` (example only). Use the **Controller API**, not the MCP
  gateway endpoint.
- Values provided at runtime: numeric `project_id`, the relative `playbook_path`
  in the Project, and the full approved Git commit SHA (`expected_revision`).
  Do not rely on environment-specific default project IDs or hostnames.
- `AAP_API_TOKEN` delivered via a secure environment/secret store, or a private
  credentials file supported by the helper. Never print or commit the token.

## Approval and safety rules

1. Do **not** run before `/agentic-sre-remediate` has recorded its **Git
   commit/push approval** (`approve-git`), the approved changes have been pushed,
   and the intended branch and exact commit SHA are known.
2. Project synchronization does **not** grant permission to execute remediation.
   The separate **Remediation execution** gate (`approve-remediate`) still applies.
3. Treat any failed Project Update, missing or ambiguous SCM revision,
   mismatching revision, missing playbook, or unavailable verification as a
   blocking error. Stop; never silently continue to Job Template execution.
4. Do not change AAP credentials, Project SCM settings, or the repository branch
   implicitly. Do not expose environment, job output, tokens or host inventory
   in logs/public documentation.

## Procedure

1. **Resolve the target**: obtain the explicitly configured Project ID and
   playbook path. Ensure the Project points to the approved Git repository and
   intended branch. If either is unknown, stop and request configuration.
2. **Establish expected revision**: obtain the complete 40-character Git SHA of
   the commit approved and pushed (`git rev-parse HEAD` can help when HEAD is the
   pushed commit; verify remote branch state before trusting it). Record it.
3. **Check access without changing the Project** (optional but recommended):

   ```bash
   python3 scripts/aap_project_sync.py \
     --project-id "$AAP_PROJECT_ID" --check-auth-only
   ```

4. **Start and monitor SCM synchronization** using the same shared helper:

   ```bash
   python3 scripts/aap_project_sync.py \
     --project-id "$AAP_PROJECT_ID" \
     --expected-revision "$APPROVED_GIT_SHA"
   ```

   Run this from the cloned repository root, after `AAP_CONTROLLER_URL` and
   `AAP_API_TOKEN` have been securely configured in the execution environment.
   The helper polls the AAP Project Update until it finishes or times out, and
   returns a nonzero exit status if the update fails or the revision differs.
5. **Verify the playbook**: independently query the AAP Controller Project's
   available playbooks using the AAP MCP `playbooks` listing (or equivalent
   authorized read-only Controller API). Require an exact match for
   `playbook_path` before proceeding. The script does **not** perform this
   separate playbook-list check.
6. **Return evidence to the orchestrator**: Project ID/name, Project Update ID,
   terminal update status, expected and observed SCM revision, target playbook
   path and playbook visibility. Keep host and job evidence in private reporting.

## Result

- `SYNC_VERIFIED`: update succeeded, full SCM SHA matches approved Git commit,
  and the expected playbook is visible in the Project.
- `SYNC_FAILED`: update failed, timed out, or returned a different SCM SHA.
- `PLAYBOOK_NOT_VERIFIED`: SCM revision matched, but the expected playbook could
  not be proven available in AAP.

Only `SYNC_VERIFIED` allows the orchestrator to **prepare** the Job Template.
The skill must never launch remediation on its own.

## Limitations

- This skill is instruction-driven orchestration, not a standalone agent runtime.
  An agent must have permission to invoke the helper and AAP MCP tools.
- The shared helper enforces revision equality **only when**
  `--expected-revision` is supplied. The orchestrated path requires it.
- AAP may have different API routes or SCM behaviours across versions; verify
  compatibility in a non-production environment before relying on this workflow.
