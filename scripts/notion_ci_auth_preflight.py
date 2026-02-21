#!/usr/bin/env python3
"""Preflight checker for Notion zero-touch sync CI workflow (fail-closed)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_context(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path | None, payload: dict) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_notion_token(token: str) -> tuple[bool, int, str]:
    req = request.Request(
        "https://api.notion.com/v1/users/me",
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
        },
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            status = response.getcode()
            body = response.read().decode("utf-8", errors="replace")
            if status == 200:
                return True, status, body
            return False, status, body
    except error.HTTPError as http_err:
        body = http_err.read().decode("utf-8", errors="replace")
        return False, http_err.code, body
    except Exception as exc:  # pragma: no cover - defensive runtime branch
        return False, -1, f"{type(exc).__name__}: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Notion CI auth preflight")
    parser.add_argument("--context-json", required=False)
    parser.add_argument("--output", required=False)
    parser.add_argument("--github-output", required=False)
    args = parser.parse_args()

    context = load_context(Path(args.context_json) if args.context_json else None)
    changed_targets = context.get("changed_targets", [])
    changed = bool(changed_targets)
    already_synced = bool(context.get("already_synced", False))

    result: dict[str, object] = {
        "checked_at_utc": now_utc_iso(),
        "changed_targets_count": len(changed_targets),
        "changed_targets": changed_targets,
        "already_synced": already_synced,
        "status": "SKIP",
        "error_code": "",
        "message": "",
        "runbook": "docs/ops/runbook_spec_notion_gate.md",
    }

    if not changed or already_synced:
        result["status"] = "SKIP"
        result["message"] = "No Notion auth preflight needed (no sync target change or already synced)."
        write_json(Path(args.output) if args.output else None, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    notion_token = os.getenv("NOTION_TOKEN", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not notion_token:
        result["status"] = "FAIL"
        result["error_code"] = "NOTION_AUTH_TOKEN_MISSING"
        result["message"] = (
            "Fail-Closed: NOTION_TOKEN is missing. "
            "Update CI secret and follow docs/ops/runbook_spec_notion_gate.md."
        )
        write_json(Path(args.output) if args.output else None, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    if not openai_api_key:
        result["status"] = "FAIL"
        result["error_code"] = "OPENAI_API_KEY_MISSING"
        result["message"] = (
            "Fail-Closed: OPENAI_API_KEY is missing. "
            "Codex sync step cannot run without it."
        )
        write_json(Path(args.output) if args.output else None, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3

    ok, status_code, raw = verify_notion_token(notion_token)
    result["notion_http_status"] = status_code
    if ok:
        result["status"] = "PASS"
        result["error_code"] = ""
        result["message"] = "Notion token preflight passed."
    else:
        result["status"] = "FAIL"
        if status_code == 401:
            result["error_code"] = "NOTION_AUTH_UNAUTHORIZED"
            result["message"] = (
                "Fail-Closed: Notion token unauthorized (401). "
                "Rotate token and validate workspace access."
            )
        elif status_code == 403:
            result["error_code"] = "NOTION_AUTH_FORBIDDEN"
            result["message"] = (
                "Fail-Closed: Notion token forbidden (403). "
                "Grant page/database permissions to integration."
            )
        else:
            result["error_code"] = "NOTION_AUTH_PRECHECK_FAILED"
            result["message"] = (
                f"Fail-Closed: Notion preflight failed (status={status_code}). "
                "Check network/token/workspace permissions."
            )
        result["detail"] = raw[:1200]

    write_json(Path(args.output) if args.output else None, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.github_output:
        gh = Path(args.github_output)
        with gh.open("a", encoding="utf-8") as fh:
            fh.write(f"notion_preflight_status={result['status']}\n")
            fh.write(f"notion_preflight_error_code={result['error_code']}\n")
            fh.write(f"notion_preflight_message={str(result['message']).replace(chr(10), ' ')}\n")

    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
