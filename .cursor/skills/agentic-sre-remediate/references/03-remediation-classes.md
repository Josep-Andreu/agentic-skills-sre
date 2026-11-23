# Remediation classes

Select the class from **local** evidence + advisory metadata. Do not assume kernel or reboot.

| Class | Typical signals | Reboot? | Notes |
|-------|-----------------|---------|-------|
| `package` | RPM/DNF advisory packages; userspace libs/apps | Usually no | Pin EVR/`state: present`; avoid blanket upgrade |
| `service` | Fixed package already installed; service still vulnerable mode | No | Restart/reload only if plan approved |
| `config` | Misconfiguration / Advisor-style fix | No | Idempotent file/lineinfile/template |
| `kernel+reboot` | Kernel/KBI packages; running kernel older than fixed | **Yes** | Reboot must appear in plan + Gate 4 |
| `other` | Module blacklists, sysctl, etc. | Case-by-case | Document explicitly |
| `none` | Already fixed or not applicable | No | Planning decision `NO_ACTION_REQUIRED` |

## Reboot detection heuristics

Mark reboot **required** only when evidence supports it, for example:

- Target package is kernel / kernel-core / kmod affecting running kernel and running release &lt; fixed
- Vendor advisory or `needs-restarting -r` indicates reboot after the planned change
- Operator explicitly requires reboot in the approved plan

Otherwise reboot = **no**.

## Privileges

- Default: assume `become` only if package install, kernel, or privileged file/service changes are in plan
- Never disable SELinux, firewalld, or sudoers restrictions to make a task succeed
