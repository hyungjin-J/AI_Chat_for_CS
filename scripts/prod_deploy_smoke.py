#!/usr/bin/env python3
"""Production deploy smoke with Docker preflight classification and evidence output."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

DEFAULT_SSOT_COMPOSE = Path("infra/compose/production/docker-compose.prod.yml")
DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_HEALTH_PATH = "/actuator/health"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIPPED = "SKIPPED"

REASON_NONE = "NONE"
REASON_DOCKER_ENGINE_DOWN = "DOCKER_ENGINE_DOWN"
REASON_DOCKER_PERMISSION = "DOCKER_PERMISSION"
REASON_DOCKER_COMPOSE_UNAVAILABLE = "DOCKER_COMPOSE_UNAVAILABLE"
REASON_COMPOSE_FILE_MISSING = "COMPOSE_FILE_MISSING"
REASON_COMPOSE_FILE_MISMATCH = "COMPOSE_FILE_MISMATCH"
REASON_COMPOSE_DOWN_FAIL = "COMPOSE_DOWN_FAIL"
REASON_COMPOSE_UP_FAIL = "COMPOSE_UP_FAIL"
REASON_PORT_CONFLICT = "PORT_CONFLICT"
REASON_FLYWAY_FAIL = "FLYWAY_FAIL"
REASON_HEALTHCHECK_FAIL = "HEALTHCHECK_FAIL"
REASON_UNKNOWN = "UNKNOWN"

DOCKER_ENGINE_TOKENS = (
    "failed to connect to the docker api",
    "cannot connect to the docker daemon",
    "is the docker daemon running",
    "daemon is running",
    "dockerdesktoplinuxengine",
    "open //./pipe/dockerdesktoplinuxengine",
    "error during connect",
)
DOCKER_PERMISSION_TOKENS = (
    "permission denied",
    "access is denied",
    "got permission denied while trying to connect",
)
PORT_CONFLICT_TOKENS = (
    "port is already allocated",
    "address already in use",
    "bind: only one usage of each socket address",
)
SENSITIVE_REPLACEMENTS = (
    (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)([A-Za-z0-9._\-+/=]+)"),
        r"\1<REDACTED>",
    ),
    (
        re.compile(r"(?i)\b(password|secret|token|api[-_]?key)\b\s*[:=]\s*([^\s,;]+)"),
        r"\1=<REDACTED>",
    ),
    (
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "<REDACTED_EMAIL>",
    ),
    (
        re.compile(r"(?:\+\d{1,3}[- ]?)?(?:\d{2,4}[- ]?){2}\d{4}\b"),
        "<REDACTED_PHONE>",
    ),
)

REMEDIATION_BY_REASON = {
    REASON_NONE: "-",
    REASON_DOCKER_ENGINE_DOWN: (
        "Start Docker Desktop/Engine, verify `docker info` returns Server details, then rerun smoke."
    ),
    REASON_DOCKER_PERMISSION: (
        "Run with Docker socket/daemon access. On Windows, reopen terminal with Docker Desktop permissions."
    ),
    REASON_DOCKER_COMPOSE_UNAVAILABLE: "Install/repair Docker Compose v2 plugin and rerun smoke.",
    REASON_COMPOSE_FILE_MISSING: "Verify SSOT compose path exists: infra/compose/production/docker-compose.prod.yml.",
    REASON_COMPOSE_FILE_MISMATCH: "Use only SSOT compose path: infra/compose/production/docker-compose.prod.yml.",
    REASON_COMPOSE_DOWN_FAIL: "Inspect compose daemon logs and clear stale resources, then rerun.",
    REASON_COMPOSE_UP_FAIL: "Fix compose startup failure from command stderr and rerun smoke.",
    REASON_PORT_CONFLICT: "Free conflicting ports or adjust host port mappings before rerun.",
    REASON_FLYWAY_FAIL: (
        "Verify backend migration startup and `flyway_schema_history` creation in PostgreSQL."
    ),
    REASON_HEALTHCHECK_FAIL: (
        "Check backend container logs and health endpoint contract (without trace=409, with trace=200)."
    ),
    REASON_UNKNOWN: "Inspect command stderr/stdout tail in this artifact and triage manually.",
}


@dataclass
class CommandRecord:
    name: str
    command: str
    exit_code: int
    duration_ms: int
    stdout_tail: str
    stderr_tail: str


@dataclass
class HttpProbeRecord:
    url: str
    expected_status: int
    actual_status: int | None
    ok: bool
    error: str
    body_excerpt: str
    attempts: int


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_text(text: str, max_chars: int = 3000) -> str:
    if not text:
        return ""
    value = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    value = "".join(ch for ch in value if ch == "\n" or ch >= " ")
    for pattern, replacement in SENSITIVE_REPLACEMENTS:
        value = pattern.sub(replacement, value)
    value = value.strip()
    if len(value) > max_chars:
        value = value[-max_chars:]
    return value


def command_to_str(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_command(
    name: str,
    command: list[str],
    records: list[CommandRecord],
    timeout_sec: int = 300,
) -> subprocess.CompletedProcess[str]:
    start = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        stdout = normalize_text(exc.stdout or "")
        stderr = normalize_text((exc.stderr or "") + "\ncommand timed out")
        records.append(
            CommandRecord(
                name=name,
                command=command_to_str(command),
                exit_code=124,
                duration_ms=duration_ms,
                stdout_tail=stdout,
                stderr_tail=stderr,
            )
        )
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + "\ncommand timed out",
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    records.append(
        CommandRecord(
            name=name,
            command=command_to_str(command),
            exit_code=proc.returncode,
            duration_ms=duration_ms,
            stdout_tail=normalize_text(proc.stdout),
            stderr_tail=normalize_text(proc.stderr),
        )
    )
    return proc


def classify_docker_failure(raw_output: str) -> str:
    value = raw_output.lower()
    if any(token in value for token in DOCKER_PERMISSION_TOKENS):
        return REASON_DOCKER_PERMISSION
    if any(token in value for token in DOCKER_ENGINE_TOKENS):
        return REASON_DOCKER_ENGINE_DOWN
    return REASON_UNKNOWN


def classify_compose_failure(raw_output: str) -> str:
    value = raw_output.lower()
    if any(token in value for token in PORT_CONFLICT_TOKENS):
        return REASON_PORT_CONFLICT
    if any(token in value for token in DOCKER_PERMISSION_TOKENS):
        return REASON_DOCKER_PERMISSION
    if any(token in value for token in DOCKER_ENGINE_TOKENS):
        return REASON_DOCKER_ENGINE_DOWN
    return REASON_COMPOSE_UP_FAIL


def compose_command(compose_path: Path, *tail: str) -> list[str]:
    return ["docker", "compose", "-f", str(compose_path), *tail]


def make_http_probe(
    url: str,
    expected_status: int,
    headers: dict[str, str],
    timeout_sec: int = 5,
) -> HttpProbeRecord:
    req = urllib_request.Request(url=url, method="GET", headers=headers)
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            status = int(resp.getcode())
            body = normalize_text(resp.read(1024).decode("utf-8", errors="replace"), max_chars=600)
            return HttpProbeRecord(
                url=url,
                expected_status=expected_status,
                actual_status=status,
                ok=status == expected_status,
                error="",
                body_excerpt=body,
                attempts=1,
            )
    except urllib_error.HTTPError as exc:
        body = normalize_text(exc.read(1024).decode("utf-8", errors="replace"), max_chars=600)
        return HttpProbeRecord(
            url=url,
            expected_status=expected_status,
            actual_status=int(exc.code),
            ok=int(exc.code) == expected_status,
            error="",
            body_excerpt=body,
            attempts=1,
        )
    except urllib_error.URLError as exc:
        return HttpProbeRecord(
            url=url,
            expected_status=expected_status,
            actual_status=None,
            ok=False,
            error=normalize_text(str(exc), max_chars=600),
            body_excerpt="",
            attempts=1,
        )


def wait_http_status(
    url: str,
    expected_status: int,
    headers: dict[str, str],
    timeout_sec: int,
    poll_interval_sec: float,
) -> HttpProbeRecord:
    deadline = time.monotonic() + max(timeout_sec, 1)
    attempts = 0
    latest = HttpProbeRecord(
        url=url,
        expected_status=expected_status,
        actual_status=None,
        ok=False,
        error="probe not executed",
        body_excerpt="",
        attempts=0,
    )
    while time.monotonic() <= deadline:
        attempts += 1
        latest = make_http_probe(url=url, expected_status=expected_status, headers=headers, timeout_sec=5)
        latest.attempts = attempts
        if latest.ok:
            return latest
        time.sleep(max(poll_interval_sec, 0.2))
    latest.attempts = attempts
    return latest


def join_url(base_url: str, path: str) -> str:
    left = base_url.rstrip("/")
    right = path if path.startswith("/") else f"/{path}"
    return f"{left}{right}"


def verify_flyway_history(
    compose_path: Path,
    records: list[CommandRecord],
    timeout_sec: int,
    poll_interval_sec: float,
) -> tuple[bool, int | None]:
    deadline = time.monotonic() + max(timeout_sec, 1)
    attempts = 0
    last_count: int | None = None
    while time.monotonic() <= deadline:
        attempts += 1
        proc = run_command(
            name=f"flyway_history_probe_{attempts}",
            command=compose_command(
                compose_path,
                "exec",
                "-T",
                "postgres",
                "sh",
                "-lc",
                (
                    'export PGPASSWORD="$POSTGRES_PASSWORD"; '
                    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At '
                    '-c "SELECT COUNT(*) FROM flyway_schema_history;"'
                ),
            ),
            records=records,
            timeout_sec=90,
        )
        if proc.returncode == 0:
            raw = (proc.stdout or "").strip().splitlines()
            candidate = raw[-1].strip() if raw else ""
            if candidate.isdigit():
                last_count = int(candidate)
                if last_count >= 1:
                    return (True, last_count)
        time.sleep(max(poll_interval_sec, 0.3))
    return (False, last_count)


def derive_json_path(out_txt: Path, out_json: str | None) -> Path:
    if out_json:
        return Path(out_json)
    if out_txt.suffix.lower() == ".txt":
        return out_txt.with_suffix(".json")
    return Path(str(out_txt) + ".json")


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run production deploy smoke with explicit reason codes")
    parser.add_argument("--ssot-compose", default=str(DEFAULT_SSOT_COMPOSE))
    parser.add_argument("--out", required=True, help="Output text artifact path")
    parser.add_argument("--out-json", help="Optional output json artifact path")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--health-path", default=DEFAULT_HEALTH_PATH)
    parser.add_argument("--startup-timeout-sec", type=int, default=240)
    parser.add_argument("--poll-interval-sec", type=float, default=3.0)
    parser.add_argument(
        "--docker-unavailable-policy",
        choices=("fail", "skipped"),
        default="fail",
        help="When docker preflight fails: fail (exit 1) or skipped (exit 0).",
    )
    return parser.parse_args()


def make_payload(
    *,
    status: str,
    reason_code: str,
    compose_display_path: str,
    base_url: str,
    health_path: str,
    policy: str,
    started_at_utc: str,
    commands: list[CommandRecord],
    flyway_row_count: int | None,
    warmup_probe: HttpProbeRecord | None,
    without_trace_probe: HttpProbeRecord | None,
    with_trace_probe: HttpProbeRecord | None,
) -> dict[str, Any]:
    finished_at_utc = now_utc_iso()
    return {
        "status": status,
        "reason_code": reason_code,
        "remediation_hint": REMEDIATION_BY_REASON.get(reason_code, REMEDIATION_BY_REASON[REASON_UNKNOWN]),
        "docker_unavailable_policy": policy,
        "ssot_compose_file": compose_display_path,
        "base_url": base_url,
        "health_path": health_path,
        "health_url": join_url(base_url, health_path),
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "flyway_row_count": flyway_row_count,
        "health_contract": {
            "without_trace_expected_status": 409,
            "without_trace_status": without_trace_probe.actual_status if without_trace_probe else None,
            "with_trace_expected_status": 200,
            "with_trace_status": with_trace_probe.actual_status if with_trace_probe else None,
            "warmup_expected_status": 200,
            "warmup_status": warmup_probe.actual_status if warmup_probe else None,
        },
        "commands": [asdict(item) for item in commands],
        "probes": {
            "warmup": asdict(warmup_probe) if warmup_probe else None,
            "without_trace": asdict(without_trace_probe) if without_trace_probe else None,
            "with_trace": asdict(with_trace_probe) if with_trace_probe else None,
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        "prod_deploy_smoke",
        f"status={payload['status']}",
        f"reason_code={payload['reason_code']}",
        f"remediation_hint={payload['remediation_hint']}",
        f"docker_unavailable_policy={payload['docker_unavailable_policy']}",
        f"ssot_compose_file={payload['ssot_compose_file']}",
        f"health_url={payload['health_url']}",
        f"flyway_row_count={payload['flyway_row_count']}",
        f"warmup_status={payload['health_contract']['warmup_status']}",
        f"without_trace_status={payload['health_contract']['without_trace_status']}",
        f"with_trace_status={payload['health_contract']['with_trace_status']}",
        f"command_count={len(payload['commands'])}",
    ]
    for command in payload["commands"]:
        lines.append(
            f"- [{command['name']}] exit_code={command['exit_code']} "
            f"duration_ms={command['duration_ms']} command={command['command']}"
        )
        if command["stdout_tail"]:
            lines.append(f"  stdout_tail={command['stdout_tail']}")
        if command["stderr_tail"]:
            lines.append(f"  stderr_tail={command['stderr_tail']}")
    return "\n".join(lines) + "\n"


def write_outputs(out_txt: Path, out_json: Path, payload: dict[str, Any]) -> None:
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text(render_text(payload), encoding="utf-8")
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    compose_path = (repo_root / args.ssot_compose).resolve() if not Path(args.ssot_compose).is_absolute() else Path(args.ssot_compose).resolve()
    expected_ssot = (repo_root / DEFAULT_SSOT_COMPOSE).resolve()
    out_txt = Path(args.out)
    out_json = derive_json_path(out_txt=out_txt, out_json=args.out_json)

    command_records: list[CommandRecord] = []
    started_at = now_utc_iso()
    compose_display_path = display_path(compose_path, repo_root)
    warmup_probe: HttpProbeRecord | None = None
    without_trace_probe: HttpProbeRecord | None = None
    with_trace_probe: HttpProbeRecord | None = None
    flyway_row_count: int | None = None

    def finish(status: str, reason_code: str) -> int:
        payload = make_payload(
            status=status,
            reason_code=reason_code,
            compose_display_path=compose_display_path,
            base_url=args.base_url,
            health_path=args.health_path,
            policy=args.docker_unavailable_policy,
            started_at_utc=started_at,
            commands=command_records,
            flyway_row_count=flyway_row_count,
            warmup_probe=warmup_probe,
            without_trace_probe=without_trace_probe,
            with_trace_probe=with_trace_probe,
        )
        write_outputs(out_txt=out_txt, out_json=out_json, payload=payload)
        if status == STATUS_PASS:
            return 0
        if status == STATUS_SKIPPED:
            return 0
        return 1

    if compose_path != expected_ssot:
        return finish(status=STATUS_FAIL, reason_code=REASON_COMPOSE_FILE_MISMATCH)

    if not compose_path.exists():
        return finish(status=STATUS_FAIL, reason_code=REASON_COMPOSE_FILE_MISSING)

    docker_info = run_command(
        name="docker_info",
        command=["docker", "info"],
        records=command_records,
        timeout_sec=60,
    )
    if docker_info.returncode != 0:
        reason_code = classify_docker_failure((docker_info.stdout or "") + "\n" + (docker_info.stderr or ""))
        if reason_code == REASON_UNKNOWN:
            reason_code = REASON_DOCKER_ENGINE_DOWN
        status = STATUS_FAIL if args.docker_unavailable_policy == "fail" else STATUS_SKIPPED
        return finish(status=status, reason_code=reason_code)

    compose_version = run_command(
        name="docker_compose_version",
        command=["docker", "compose", "version"],
        records=command_records,
        timeout_sec=30,
    )
    if compose_version.returncode != 0:
        return finish(status=STATUS_FAIL, reason_code=REASON_DOCKER_COMPOSE_UNAVAILABLE)

    compose_down = run_command(
        name="compose_down_v",
        command=compose_command(compose_path, "down", "-v", "--remove-orphans"),
        records=command_records,
        timeout_sec=180,
    )
    if compose_down.returncode != 0:
        reason = classify_compose_failure((compose_down.stdout or "") + "\n" + (compose_down.stderr or ""))
        if reason == REASON_COMPOSE_UP_FAIL:
            reason = REASON_COMPOSE_DOWN_FAIL
        return finish(status=STATUS_FAIL, reason_code=reason)

    compose_up = run_command(
        name="compose_up_d",
        command=compose_command(compose_path, "up", "-d"),
        records=command_records,
        timeout_sec=300,
    )
    if compose_up.returncode != 0:
        reason = classify_compose_failure((compose_up.stdout or "") + "\n" + (compose_up.stderr or ""))
        return finish(status=STATUS_FAIL, reason_code=reason)

    flyway_ok, flyway_row_count = verify_flyway_history(
        compose_path=compose_path,
        records=command_records,
        timeout_sec=args.startup_timeout_sec,
        poll_interval_sec=args.poll_interval_sec,
    )
    if not flyway_ok:
        return finish(status=STATUS_FAIL, reason_code=REASON_FLYWAY_FAIL)

    health_url = join_url(args.base_url, args.health_path)
    trace_id = str(uuid.uuid4())
    warmup_probe = wait_http_status(
        url=health_url,
        expected_status=200,
        headers={"X-Trace-Id": trace_id},
        timeout_sec=args.startup_timeout_sec,
        poll_interval_sec=args.poll_interval_sec,
    )
    if not warmup_probe.ok:
        return finish(status=STATUS_FAIL, reason_code=REASON_HEALTHCHECK_FAIL)

    without_trace_probe = make_http_probe(url=health_url, expected_status=409, headers={})
    if not without_trace_probe.ok:
        return finish(status=STATUS_FAIL, reason_code=REASON_HEALTHCHECK_FAIL)

    with_trace_probe = make_http_probe(
        url=health_url,
        expected_status=200,
        headers={"X-Trace-Id": str(uuid.uuid4())},
    )
    if not with_trace_probe.ok:
        return finish(status=STATUS_FAIL, reason_code=REASON_HEALTHCHECK_FAIL)

    return finish(status=STATUS_PASS, reason_code=REASON_NONE)


if __name__ == "__main__":
    raise SystemExit(main())
