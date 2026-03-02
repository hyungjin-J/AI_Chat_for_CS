#!/usr/bin/env python3
"""Verify backend health trace contract (without trace=409, with trace=200) with always-write artifacts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request


STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_SKIPPED = "SKIPPED"

REASON_NONE = "NONE"
REASON_DOCKER_ENGINE_DOWN = "DOCKER_ENGINE_DOWN"
REASON_DOCKER_PERMISSION = "DOCKER_PERMISSION"
REASON_TARGET_UNREACHABLE = "TARGET_UNREACHABLE"
REASON_HEALTH_TRACE_CONTRACT_FAIL = "HEALTH_TRACE_CONTRACT_FAIL"
REASON_UNKNOWN = "UNKNOWN"
REASON_UNEXPECTED_ERROR = "UNEXPECTED_ERROR"

DOCKER_ENGINE_TOKENS = (
    "failed to connect to the docker api",
    "cannot connect to the docker daemon",
    "is the docker daemon running",
    "dockerdesktoplinuxengine",
    "open //./pipe/dockerdesktoplinuxengine",
    "error during connect",
)
DOCKER_PERMISSION_TOKENS = (
    "permission denied",
    "access is denied",
    "got permission denied while trying to connect",
)

REMEDIATION_HINTS = {
    REASON_NONE: "-",
    REASON_DOCKER_ENGINE_DOWN: "Start Docker Desktop/Engine and verify `docker info` succeeds.",
    REASON_DOCKER_PERMISSION: "Grant Docker daemon access to this terminal/session and rerun.",
    REASON_TARGET_UNREACHABLE: "Ensure backend is running and reachable at the configured health endpoint.",
    REASON_HEALTH_TRACE_CONTRACT_FAIL: "Fix health endpoint contract: without trace=409 and with trace=200.",
    REASON_UNKNOWN: "Inspect raw response/error details in this artifact and triage manually.",
    REASON_UNEXPECTED_ERROR: "Inspect exception details in this artifact and rerun after fix.",
}


@dataclass
class Violation:
    code: str
    message: str
    details: str


@dataclass
class ProbeResult:
    status_code: int | None
    error: str
    raw_response: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run DB backend health trace contract gate")
    parser.add_argument("--endpoint", default="http://localhost:8080/actuator/health")
    parser.add_argument("--trace-header", default="X-Trace-Id")
    parser.add_argument("--trace-id", default="11111111-1111-1111-1111-111111111111")
    parser.add_argument("--without-trace-expected", type=int, default=409)
    parser.add_argument("--with-trace-expected", type=int, default=200)
    parser.add_argument("--readiness-timeout-sec", type=int, default=0)
    parser.add_argument("--poll-interval-sec", type=float, default=2.0)
    parser.add_argument("--http-timeout-sec", type=float, default=5.0)
    parser.add_argument("--docker-preflight", action="store_true")
    parser.add_argument("--docker-unavailable-policy", choices=("fail", "skipped"), default="fail")
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    parser.add_argument("--without-trace-raw")
    parser.add_argument("--with-trace-raw")
    return parser.parse_args()


def normalize_text(text: str, max_chars: int = 5000) -> str:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    value = "".join(ch for ch in value if ch == "\n" or ch >= " ")
    value = value.strip()
    if len(value) > max_chars:
        return value[-max_chars:]
    return value


def write_output(path: str | None, content: str) -> None:
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def run_subprocess(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def classify_docker_failure(raw_output: str) -> str:
    value = raw_output.lower()
    if any(token in value for token in DOCKER_PERMISSION_TOKENS):
        return REASON_DOCKER_PERMISSION
    if any(token in value for token in DOCKER_ENGINE_TOKENS):
        return REASON_DOCKER_ENGINE_DOWN
    return REASON_UNKNOWN


def run_docker_preflight() -> tuple[bool, str]:
    proc = run_subprocess(["docker", "info", "--format", "{{json .ServerErrors}}"])
    output = normalize_text((proc.stdout or "") + "\n" + (proc.stderr or ""))
    return (proc.returncode == 0, output)


def probe_endpoint(url: str, headers: dict[str, str], timeout_sec: float) -> ProbeResult:
    req = urllib_request.Request(url=url, method="GET", headers=headers)
    try:
        with urllib_request.urlopen(req, timeout=timeout_sec) as resp:
            status = int(resp.getcode())
            body = normalize_text(resp.read(2000).decode("utf-8", errors="replace"), max_chars=1200)
            raw = normalize_text(f"HTTP {status}\n{body}", max_chars=2500)
            return ProbeResult(status_code=status, error="", raw_response=raw)
    except urllib_error.HTTPError as exc:
        body = normalize_text(exc.read(2000).decode("utf-8", errors="replace"), max_chars=1200)
        status = int(exc.code)
        raw = normalize_text(f"HTTP {status}\n{body}", max_chars=2500)
        return ProbeResult(status_code=status, error="", raw_response=raw)
    except urllib_error.URLError as exc:
        error_text = normalize_text(str(exc), max_chars=800)
        return ProbeResult(status_code=None, error=error_text, raw_response=error_text)


def wait_with_trace_status(
    endpoint: str,
    headers: dict[str, str],
    expected_status: int,
    timeout_sec: int,
    poll_interval_sec: float,
    http_timeout_sec: float,
) -> tuple[ProbeResult, int]:
    if timeout_sec <= 0:
        result = probe_endpoint(endpoint, headers, http_timeout_sec)
        return (result, 1)

    deadline = time.monotonic() + max(timeout_sec, 1)
    attempts = 0
    latest = ProbeResult(status_code=None, error="probe_not_executed", raw_response="")
    while time.monotonic() <= deadline:
        attempts += 1
        latest = probe_endpoint(endpoint, headers, http_timeout_sec)
        if latest.status_code == expected_status:
            return (latest, attempts)
        time.sleep(max(poll_interval_sec, 0.2))
    return (latest, attempts)


def make_payload(
    *,
    status: str,
    reason_code: str,
    endpoint: str,
    trace_header: str,
    without_trace_expected: int,
    with_trace_expected: int,
    without_trace_result: ProbeResult,
    with_trace_result: ProbeResult,
    with_trace_attempts: int,
    docker_preflight_status: str,
    violations: list[Violation],
) -> dict:
    return {
        "status": status,
        "reason_code": reason_code,
        "remediation_hint": REMEDIATION_HINTS.get(reason_code, REMEDIATION_HINTS[REASON_UNKNOWN]),
        "endpoint": endpoint,
        "trace_header": trace_header,
        "without_trace_expected": without_trace_expected,
        "without_trace_status": without_trace_result.status_code,
        "without_trace_error": without_trace_result.error,
        "with_trace_expected": with_trace_expected,
        "with_trace_status": with_trace_result.status_code,
        "with_trace_error": with_trace_result.error,
        "with_trace_attempts": with_trace_attempts,
        "docker_preflight_status": docker_preflight_status,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }


def render_text(payload: dict) -> str:
    lines = [
        "db_backend_health_trace_gate",
        f"status={payload['status']}",
        f"reason_code={payload['reason_code']}",
        f"remediation_hint={payload['remediation_hint']}",
        f"endpoint={payload['endpoint']}",
        f"docker_preflight_status={payload['docker_preflight_status']}",
        f"without_trace_status={payload['without_trace_status']}",
        f"without_trace_expected={payload['without_trace_expected']}",
        f"with_trace_status={payload['with_trace_status']}",
        f"with_trace_expected={payload['with_trace_expected']}",
        f"with_trace_attempts={payload['with_trace_attempts']}",
        f"violation_count={payload['violation_count']}",
    ]
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['message']} :: {violation['details']}")
    return "\n".join(lines) + "\n"


def execute(args: argparse.Namespace) -> tuple[dict, ProbeResult, ProbeResult]:
    violations: list[Violation] = []
    status = STATUS_PASS
    reason_code = REASON_NONE
    docker_preflight_status = "NOT_REQUIRED"
    without_trace = ProbeResult(status_code=None, error="", raw_response="")
    with_trace = ProbeResult(status_code=None, error="", raw_response="")
    with_trace_attempts = 0

    if args.docker_preflight:
        docker_ok, docker_output = run_docker_preflight()
        if not docker_ok:
            reason_code = classify_docker_failure(docker_output)
            violations.append(
                Violation(
                    code=reason_code,
                    message="docker preflight failed",
                    details=docker_output,
                )
            )
            docker_preflight_status = "FAIL"
            status = STATUS_SKIPPED if args.docker_unavailable_policy == "skipped" else STATUS_FAIL
            payload = make_payload(
                status=status,
                reason_code=reason_code,
                endpoint=args.endpoint,
                trace_header=args.trace_header,
                without_trace_expected=args.without_trace_expected,
                with_trace_expected=args.with_trace_expected,
                without_trace_result=without_trace,
                with_trace_result=with_trace,
                with_trace_attempts=with_trace_attempts,
                docker_preflight_status=docker_preflight_status,
                violations=violations,
            )
            return payload, without_trace, with_trace
        docker_preflight_status = "PASS"

    with_trace, with_trace_attempts = wait_with_trace_status(
        endpoint=args.endpoint,
        headers={args.trace_header: args.trace_id},
        expected_status=args.with_trace_expected,
        timeout_sec=args.readiness_timeout_sec,
        poll_interval_sec=args.poll_interval_sec,
        http_timeout_sec=args.http_timeout_sec,
    )

    without_trace = probe_endpoint(
        args.endpoint,
        headers={},
        timeout_sec=args.http_timeout_sec,
    )

    if without_trace.status_code != args.without_trace_expected:
        violations.append(
            Violation(
                code="HEALTH_TRACE_CONTRACT",
                message="without trace status mismatch",
                details=f"expected={args.without_trace_expected} actual={without_trace.status_code}",
            )
        )

    if with_trace.status_code != args.with_trace_expected:
        violations.append(
            Violation(
                code="HEALTH_TRACE_CONTRACT",
                message="with trace status mismatch",
                details=f"expected={args.with_trace_expected} actual={with_trace.status_code}",
            )
        )

    if violations:
        status = STATUS_FAIL
        if with_trace.status_code is None and without_trace.status_code is None:
            reason_code = REASON_TARGET_UNREACHABLE
        else:
            reason_code = REASON_HEALTH_TRACE_CONTRACT_FAIL

    payload = make_payload(
        status=status,
        reason_code=reason_code,
        endpoint=args.endpoint,
        trace_header=args.trace_header,
        without_trace_expected=args.without_trace_expected,
        with_trace_expected=args.with_trace_expected,
        without_trace_result=without_trace,
        with_trace_result=with_trace,
        with_trace_attempts=with_trace_attempts,
        docker_preflight_status=docker_preflight_status,
        violations=violations,
    )
    return payload, without_trace, with_trace


def main() -> int:
    args = parse_args()
    try:
        payload, without_trace, with_trace = execute(args)
    except Exception as exc:  # pragma: no cover - always-write safety net
        without_trace = ProbeResult(status_code=None, error="", raw_response="")
        with_trace = ProbeResult(status_code=None, error="", raw_response="")
        payload = make_payload(
            status=STATUS_FAIL,
            reason_code=REASON_UNEXPECTED_ERROR,
            endpoint=args.endpoint,
            trace_header=args.trace_header,
            without_trace_expected=args.without_trace_expected,
            with_trace_expected=args.with_trace_expected,
            without_trace_result=without_trace,
            with_trace_result=with_trace,
            with_trace_attempts=0,
            docker_preflight_status="UNKNOWN",
            violations=[
                Violation(
                    code=REASON_UNEXPECTED_ERROR,
                    message="unexpected exception in db_backend_health_trace_gate",
                    details=normalize_text(str(exc)),
                )
            ],
        )

    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    write_output(args.output_txt, text_report)
    write_output(args.output_json, json_report)
    write_output(args.without_trace_raw, without_trace.raw_response + ("\n" if without_trace.raw_response else ""))
    write_output(args.with_trace_raw, with_trace.raw_response + ("\n" if with_trace.raw_response else ""))

    sys.stdout.write(text_report)
    if payload["status"] in {STATUS_PASS, STATUS_SKIPPED}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
