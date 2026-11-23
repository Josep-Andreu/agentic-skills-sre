# Local Applicability Probe — AAP setup and interpretation

This is a **read-only evidence collection playbook** for RPM/advisory-based
vulnerabilities on RHEL-family hosts. It is not a universal CVE applicability
checker and it does not modify packages, configurations or services.

## Configure once in Ansible Automation Platform

1. Ensure the AAP SCM Project already includes
   `playbooks/local-applicability-probe.yml` and has been synchronized.
2. Create a dedicated Job Template using that playbook and a credential with
   only the privileges necessary for read-only checks.
3. **Before every launch**, require the workflow's `approve-probe` gate and set
   the Job Template **Limit** to exactly one inventory hostname. Do not leave
   Limit empty or use `all` / group patterns.
4. Supply the following `extra_vars` (adapted to a verified advisory):

```yaml
expected_hostname: host.example.org  # exact AAP inventory_hostname
# Historical illustrative identifiers; independently validate advisories.
target_cve: CVE-2026-114406
target_advisory: RHSA-2026:88459
target_packages:
  - ca-certificates
# Optional, for human/agent evaluation. The playbook DOES NOT compare EVRs.
fixed_evr_by_package:
  ca-certificates: '0:2026.2.92_v9.0.319-90.3.el9_8'
```

The playbook checks that only the explicitly named inventory host is in the
run; it refuses a broad target even if the AAP Limit was misconfigured. It
validates privilege escalation (`id -u`), collects minimal OS and kernel facts,
queries RPM package NEVRAs and asks DNF about cached updates for the advisory.
Using `--cacheonly` avoids refreshing repository metadata; unavailable cache
may make results partial.

Results appear in the AAP job output as `agentic_probe` and are also emitted
via `ansible.builtin.set_stats` where supported by the Controller/EE.

## Interpreting the output

- `evidence_status: COLLECTED` means the requested RPM queries and cached DNF
  query completed; it **does not** prove a CVE is fixed or vulnerable.
- `evidence_status: PARTIAL` means one or more queries could not provide
  complete evidence; this must **not** yield `NO_ACTION_REQUIRED`.
- `planning_decision: REVIEW_REQUIRED` is intentionally constant. The
  orchestrator must combine the observations with **vendor-validated** fixed
  EVRs (including RPM epoch/backports), product/OS/architecture applicability,
  and any relevant runtime/configuration checks.
- A missing DNF update in a cached advisory listing never proves that the
  vulnerability has been remediated.
- For kernel, configuration, service or non-RPM vulnerabilities, use a separate
  specifically reviewed probe or additional explicitly approved read-only
  checks; `uname -r` alone cannot establish security applicability.

The probe is not a substitute for independent post-remediation verification.
Historical jobs should never be treated as evidence of current host state.

## Local validation (no target host contacted)

```bash
ansible-playbook --syntax-check playbooks/local-applicability-probe.yml
```

This checks syntax only. Validate actual target scope, Controller behavior,
`set_stats` output and `dnf --cacheonly` behavior in a test AAP environment.
