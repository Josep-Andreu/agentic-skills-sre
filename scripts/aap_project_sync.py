#!/usr/bin/env python3
"""Synchronize an AAP Controller project from SCM and wait until successful.

Loads credentials from the environment or from
~/.config/agentic-sre/credentials (sourced as KEY=VALUE / export KEY=VALUE).

Never prints token values.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_CONTROLLER = ""
DEFAULT_PROJECT_ID = 0
DEFAULT_CREDENTIALS_FILE = Path.home() / ".config" / "agentic-sre" / "credentials"
POLL_INTERVAL_SEC = 3
DEFAULT_TIMEOUT_SEC = 300


def _load_credentials_file(path: Path) -> None:
    """Load KEY=VALUE lines into os.environ without printing values."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def _controller_base() -> str:
    # Prefer explicit controller URL. Do not use AAP_MCP_SERVER (:8448 MCP gateway).
    for key in ("AAP_CONTROLLER_URL", "CONTROLLER_HOST", "AAP_HOST", "AAP_URL"):
        val = (os.environ.get(key) or "").strip().rstrip("/")
        if not val:
            continue
        if not val.startswith("http"):
            val = "https://" + val
        parsed = urlparse(val)
        # If someone pointed this at the MCP gateway port, strip to host default HTTPS.
        if parsed.port == 8448:
            return f"{parsed.scheme}://{parsed.hostname}"
        return f"{parsed.scheme}://{parsed.hostname}" + (
            f":{parsed.port}" if parsed.port and parsed.port not in (80, 443) else ""
        )
    raise RuntimeError("Set AAP_CONTROLLER_URL (no built-in production endpoint)")


def _token() -> str:
    for key in ("AAP_API_TOKEN", "CONTROLLER_OAUTH_TOKEN", "TOWER_TOKEN", "AWX_TOKEN"):
        val = (os.environ.get(key) or "").strip()
        if val:
            # Accept accidental "Bearer xxx"
            if val.lower().startswith("bearer "):
                return val.split(None, 1)[1].strip()
            return val
    return ""


def _request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 60,
) -> tuple[int, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            data: Any = json.loads(raw) if raw else {}
            return resp.status, data
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        err_body = err_body.replace(token, "***")
        raise RuntimeError(f"HTTP {exc.code} {method} {urlparse(url).path}: {err_body[:500]}") from exc
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).replace(token, "***")
        raise RuntimeError(f"{type(exc).__name__} {method} {urlparse(url).path}: {msg}") from exc


def _require_full_revision(value: str) -> str:
    """Require a complete Git SHA rather than accepting ambiguous short prefixes."""
    expected = value.strip().lower()
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", expected):
        raise ValueError("Expected revision must be a full 40- or 64-character Git SHA")
    return expected


def _ensure_revision_matches(expected: str, observed: str | None) -> None:
    """Fail closed when an SCM Project resolves to an unexpected commit."""
    observed_normalized = (observed or "").strip().lower()
    if observed_normalized != expected:
        raise RuntimeError(
            "AAP SCM revision mismatch: "
            f"expected={expected[:12]} observed={observed_normalized[:12] or 'missing'}"
        )


def sync_project(project_id: int, timeout_sec: int, expected_revision: str | None = None) -> dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError(
            "No AAP API token found. Set AAP_API_TOKEN or add it to "
            f"{DEFAULT_CREDENTIALS_FILE} (never commit this file)."
        )

    base = _controller_base().rstrip("/")
    status, project = _request("GET", f"{base}/api/controller/v2/projects/{project_id}/", token)
    if status != 200:
        raise RuntimeError(f"Unexpected status retrieving project {project_id}: {status}")

    print(
        f"Project {project_id} ({project.get('name')}) current status="
        f"{project.get('status')} revision={(project.get('scm_revision') or '')[:12]}"
    )

    print(f"POST {base}/api/controller/v2/projects/{project_id}/update/")
    status, update = _request(
        "POST",
        f"{base}/api/controller/v2/projects/{project_id}/update/",
        token,
        payload={},
    )
    if status not in (200, 201, 202):
        raise RuntimeError(f"Unexpected status starting project update: {status}")

    update_id = update.get("id")
    if not update_id:
        raise RuntimeError("Project update response missing id")

    print(f"Project update id={update_id}; polling until complete (timeout={timeout_sec}s)")
    deadline = time.time() + timeout_sec
    final: dict[str, Any] = {}
    while time.time() < deadline:
        _, final = _request(
            "GET",
            f"{base}/api/controller/v2/project_updates/{update_id}/",
            token,
        )
        st = final.get("status")
        print(f"  update status={st} failed={final.get('failed')} elapsed={final.get('elapsed')}")
        if st in ("successful", "failed", "error", "canceled"):
            break
        time.sleep(POLL_INTERVAL_SEC)
    else:
        raise RuntimeError(f"Timed out waiting for project update {update_id}")

    if final.get("status") != "successful" or final.get("failed"):
        raise RuntimeError(
            f"Project sync failed: status={final.get('status')} "
            f"explanation={final.get('job_explanation') or final.get('result_traceback') or 'n/a'}"
        )

    _, project = _request("GET", f"{base}/api/controller/v2/projects/{project_id}/", token)
    if expected_revision is not None:
        _ensure_revision_matches(expected_revision, project.get("scm_revision"))
    print(
        f"Sync successful. Project status={project.get('status')} "
        f"revision={(project.get('scm_revision') or '')[:12]}"
        + (" (approved revision matched)" if expected_revision is not None else "")
    )

    return {
        "project_id": project_id,
        "project_name": project.get("name"),
        "scm_revision": project.get("scm_revision"),
        "expected_revision": expected_revision,
        "revision_matches": (True if expected_revision is not None else None),
        "update_id": update_id,
        "status": project.get("status"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchronize an AAP Controller Git project")
    parser.add_argument("--project-id", type=int, default=int(os.environ.get("AAP_PROJECT_ID", "0")))
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument(
        "--expected-revision",
        help="Full approved Git commit SHA (40/64 hex); mismatch stops the workflow",
    )
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=DEFAULT_CREDENTIALS_FILE,
        help="Optional credentials file with AAP_API_TOKEN (never printed)",
    )
    parser.add_argument(
        "--check-auth-only",
        action="store_true",
        help="Only verify token can read the project; do not start a sync",
    )
    args = parser.parse_args(argv)

    _load_credentials_file(args.credentials_file)

    if args.project_id < 1:
        parser.error("Provide --project-id or AAP_PROJECT_ID")

    try:
        if args.check_auth_only:
            token = _token()
            if not token:
                print("AUTH_STATUS: missing token", file=sys.stderr)
                return 2
            base = _controller_base().rstrip("/")
            status, project = _request(
                "GET", f"{base}/api/controller/v2/projects/{args.project_id}/", token
            )
            print(
                f"AUTH_STATUS: ok HTTP={status} project={project.get('name')} "
                f"status={project.get('status')}"
            )
            return 0
        expected_revision = (
            _require_full_revision(args.expected_revision) if args.expected_revision else None
        )
        result = sync_project(args.project_id, args.timeout, expected_revision=expected_revision)
        print(json.dumps({"ok": True, **result}, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
