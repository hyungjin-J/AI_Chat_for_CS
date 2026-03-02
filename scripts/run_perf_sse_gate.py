#!/usr/bin/env python3
"""Run SSE perf gate with always-write result contract."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


REASON_OK = "OK"
REASON_K6_NOT_INSTALLED = "K6_NOT_INSTALLED"
REASON_DOCKER_UNAVAILABLE = "DOCKER_UNAVAILABLE"
REASON_TARGET_UNREACHABLE = "TARGET_UNREACHABLE"
REASON_K6_EXECUTION_FAILED = "K6_EXECUTION_FAILED"
REASON_RESULT_FILE_MISSING = "RESULT_FILE_MISSING"
REASON_COMPOSE_BOOTSTRAP_FAILED = "COMPOSE_BOOTSTRAP_FAILED"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def date_tag_local() -> str:
    return dt.datetime.now().strftime("%Y%m%d")


def _json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"


def _trim(text: str, limit: int = 300) -> str:
    cleaned = (text or "").replace("\r", " ").replace("\n", " ").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit]


def write_result_meta(
    result_path: Path,
    *,
    status: str,
    reason_code: str,
    reason_detail: str,
    remediation_hint: str,
    append: bool,
) -> None:
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "type": "PerfGateMeta",
        "generated_at_utc": utc_now_iso(),
        "status": status,
        "reason_code": reason_code,
        "reason_detail": reason_detail,
        "remediation_hint": remediation_hint,
    }
    mode = "a" if append else "w"
    with result_path.open(mode, encoding="utf-8", newline="\n") as handle:
        handle.write(_json_line(payload))


def is_target_reachable(base_url: str, tenant_key: str, timeout_sec: int) -> tuple[bool, str]:
    url = base_url.rstrip("/") + "/health"
    request = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "X-Trace-Id": str(uuid.uuid4()),
            "X-Tenant-Key": tenant_key,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            status = response.getcode()
            if status == 200:
                return True, ""
            return False, f"health_status={status}"
    except urllib.error.HTTPError as exc:
        return False, f"health_status={exc.code}"
    except urllib.error.URLError as exc:
        return False, f"health_network_error={exc.reason}"


def run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=None if cwd is None else str(cwd),
        env=env,
    )


def safe_stream_write(text: str, *, stderr: bool = False) -> None:
    if not text:
        return
    stream = sys.stderr if stderr else sys.stdout
    try:
        stream.write(text)
    except UnicodeEncodeError:
        encoding = stream.encoding or "utf-8"
        stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def wait_for_health(
    *,
    base_url: str,
    tenant_key: str,
    timeout_sec: int,
    retries: int,
    interval_sec: float,
) -> tuple[bool, str]:
    last_detail = "health_not_checked"
    attempts = max(1, retries)
    for idx in range(attempts):
        ok, detail = is_target_reachable(
            base_url=base_url,
            tenant_key=tenant_key,
            timeout_sec=max(1, timeout_sec),
        )
        if ok:
            return True, f"stage=health_wait attempt={idx + 1} detail={detail}"
        last_detail = detail
        if idx + 1 < attempts:
            time.sleep(max(0.1, interval_sec))
    return False, f"stage=health_wait attempts={attempts} last_detail={last_detail}"


def ensure_docker_available() -> tuple[bool, str]:
    docker_check = run_command(["docker", "info"])
    if docker_check.returncode == 0:
        return True, ""
    detail = docker_check.stderr or docker_check.stdout or "docker info failed"
    return False, _trim(detail)


def _compose_cmd(compose_file: str, command: list[str]) -> list[str]:
    return ["docker", "compose", "-f", compose_file, *command]


def bootstrap_compose_stack(args: argparse.Namespace) -> tuple[bool, str]:
    repo_root = Path(".").resolve()
    compose_file = args.compose_file
    commands: list[tuple[str, list[str], dict[str, str] | None]] = []
    commands.append(("compose_down", _compose_cmd(compose_file, ["down", "-v"]), None))
    commands.append(("compose_up_core", _compose_cmd(compose_file, ["up", "-d", "postgres", "redis"]), None))
    if not args.skip_flyway:
        commands.append(
            ("flyway_migrate", _compose_cmd(compose_file, ["--profile", "db-tools", "run", "--rm", "flyway"]), None)
        )

    backend_env = dict(os.environ)
    backend_env["APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER"] = str(args.backend_sse_concurrency_max_per_user)
    backend_env["APP_BUDGET_SSE_HOLD_MS"] = str(args.backend_sse_hold_ms)
    commands.append(
        (
            "compose_up_backend",
            _compose_cmd(compose_file, ["--profile", "demo-stack", "up", "-d", "backend"]),
            backend_env,
        )
    )

    for stage, cmd, env in commands:
        completed = run_command(cmd, cwd=repo_root, env=env)
        safe_stream_write(completed.stdout, stderr=False)
        safe_stream_write(completed.stderr, stderr=True)
        if completed.returncode != 0:
            detail = completed.stderr or completed.stdout or "compose command failed"
            return False, f"stage={stage} command_failed detail={_trim(detail)}"

    healthy, health_detail = wait_for_health(
        base_url=args.base_url,
        tenant_key=args.tenant_key,
        timeout_sec=args.health_timeout_sec,
        retries=args.health_retries,
        interval_sec=args.health_interval_sec,
    )
    if not healthy:
        return False, f"stage=post_bootstrap_health_check {health_detail}"
    return True, f"stage=bootstrap_ok {health_detail}"


def maybe_copy_dashboard_alias(gate_json: Path, date_tag: str) -> None:
    expected_primary_name = f"perf_sse_gate_{date_tag}.json"
    if gate_json.name != expected_primary_name:
        return
    alias_path = Path(f"docs/review/mvp_verification_pack/artifacts/perf_sse_gate_{date_tag}_actual.json")
    alias_path.parent.mkdir(parents=True, exist_ok=True)
    if gate_json.resolve() == alias_path.resolve():
        return
    shutil.copyfile(gate_json, alias_path)


def run_assert_gate(
    *,
    result_json: Path,
    thresholds: Path,
    gate_txt: Path,
    gate_json: Path,
) -> int:
    cmd = [
        "python",
        "perf/assert_perf_gate.py",
        "--result",
        result_json.as_posix(),
        "--thresholds",
        thresholds.as_posix(),
        "--output-txt",
        gate_txt.as_posix(),
        "--output-json",
        gate_json.as_posix(),
    ]
    completed = run_command(cmd)
    safe_stream_write(completed.stdout, stderr=False)
    safe_stream_write(completed.stderr, stderr=True)
    return int(completed.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SSE perf gate with always-write result contract")
    parser.add_argument("--result-json", default="perf/out/result.json")
    parser.add_argument("--thresholds", default="perf/thresholds.yaml")
    parser.add_argument("--k6-script", default="perf/k6/sse_load_test.js")
    parser.add_argument("--gate-txt", default="")
    parser.add_argument("--gate-json", default="")
    parser.add_argument("--k6-bin", default="k6")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--tenant-key", default="demo-tenant")
    parser.add_argument("--login-id", default="agent1")
    parser.add_argument("--password", default="agent1-pass")
    parser.add_argument("--sse-vus", default="2")
    parser.add_argument("--sse-duration", default="45s")
    parser.add_argument("--rate-limit-start-time", default="45s")
    parser.add_argument("--rate-limit-iterations", default="6")
    parser.add_argument("--health-timeout-sec", type=int, default=4)
    parser.add_argument("--health-retries", type=int, default=60)
    parser.add_argument("--health-interval-sec", type=float, default=1.0)
    parser.add_argument("--require-docker", action="store_true")
    parser.add_argument("--bootstrap-compose", action="store_true")
    parser.add_argument("--compose-file", default="infra/docker-compose.yml")
    parser.add_argument("--skip-flyway", action="store_true")
    parser.add_argument("--backend-sse-concurrency-max-per-user", default="2")
    parser.add_argument("--backend-sse-hold-ms", default="2500")
    return parser.parse_args()


def assert_and_sync(
    *,
    result_json: Path,
    thresholds: Path,
    gate_txt: Path,
    gate_json: Path,
    date_tag: str,
) -> int:
    exit_code = run_assert_gate(
        result_json=result_json,
        thresholds=thresholds,
        gate_txt=gate_txt,
        gate_json=gate_json,
    )
    maybe_copy_dashboard_alias(gate_json, date_tag)
    return exit_code


def main() -> int:
    args = parse_args()
    result_json = Path(args.result_json)
    thresholds = Path(args.thresholds)
    date_tag = date_tag_local()
    gate_txt = (
        Path(args.gate_txt)
        if args.gate_txt
        else Path(f"docs/review/mvp_verification_pack/artifacts/perf_sse_gate_{date_tag}.txt")
    )
    gate_json = (
        Path(args.gate_json)
        if args.gate_json
        else Path(f"docs/review/mvp_verification_pack/artifacts/perf_sse_gate_{date_tag}.json")
    )
    result_json.parent.mkdir(parents=True, exist_ok=True)
    gate_txt.parent.mkdir(parents=True, exist_ok=True)
    gate_json.parent.mkdir(parents=True, exist_ok=True)

    if result_json.exists():
        result_json.unlink()

    if args.require_docker or args.bootstrap_compose:
        docker_ok, docker_detail = ensure_docker_available()
        if not docker_ok:
            write_result_meta(
                result_json,
                status="FAIL",
                reason_code=REASON_DOCKER_UNAVAILABLE,
                reason_detail=f"stage=docker_preflight detail={docker_detail or 'docker info failed'}",
                remediation_hint="Start Docker engine and retry.",
                append=False,
            )
            return assert_and_sync(
                result_json=result_json,
                thresholds=thresholds,
                gate_txt=gate_txt,
                gate_json=gate_json,
                date_tag=date_tag,
            )

    if args.bootstrap_compose:
        bootstrap_ok, bootstrap_detail = bootstrap_compose_stack(args)
        if not bootstrap_ok:
            reason_code = REASON_COMPOSE_BOOTSTRAP_FAILED
            if "post_bootstrap_health_check" in bootstrap_detail:
                reason_code = REASON_TARGET_UNREACHABLE
            write_result_meta(
                result_json,
                status="FAIL",
                reason_code=reason_code,
                reason_detail=_trim(bootstrap_detail),
                remediation_hint=(
                    "Verify compose startup sequence (down/up/flyway/backend), then ensure backend /health reaches 200."
                ),
                append=False,
            )
            return assert_and_sync(
                result_json=result_json,
                thresholds=thresholds,
                gate_txt=gate_txt,
                gate_json=gate_json,
                date_tag=date_tag,
            )
    else:
        target_ok, target_detail = is_target_reachable(
            base_url=args.base_url,
            tenant_key=args.tenant_key,
            timeout_sec=max(1, args.health_timeout_sec),
        )
        if not target_ok:
            write_result_meta(
                result_json,
                status="FAIL",
                reason_code=REASON_TARGET_UNREACHABLE,
                reason_detail=f"stage=preflight_health detail={_trim(target_detail)}",
                remediation_hint="Ensure backend is running and /health returns 200 with trace/tenant headers.",
                append=False,
            )
            return assert_and_sync(
                result_json=result_json,
                thresholds=thresholds,
                gate_txt=gate_txt,
                gate_json=gate_json,
                date_tag=date_tag,
            )

    k6_path = shutil.which(args.k6_bin)
    if not k6_path:
        write_result_meta(
            result_json,
            status="FAIL",
            reason_code=REASON_K6_NOT_INSTALLED,
            reason_detail=f"k6 binary not found: {args.k6_bin}",
            remediation_hint="Install k6 and ensure it is available on PATH.",
            append=False,
        )
        return assert_and_sync(
            result_json=result_json,
            thresholds=thresholds,
            gate_txt=gate_txt,
            gate_json=gate_json,
            date_tag=date_tag,
        )

    k6_cmd = [
        k6_path,
        "run",
        args.k6_script,
        "--out",
        f"json={result_json.as_posix()}",
        "-e",
        f"BASE_URL={args.base_url}",
        "-e",
        f"TENANT_KEY={args.tenant_key}",
        "-e",
        f"LOGIN_ID={args.login_id}",
        "-e",
        f"PASSWORD={args.password}",
        "-e",
        f"SSE_VUS={args.sse_vus}",
        "-e",
        f"SSE_DURATION={args.sse_duration}",
        "-e",
        f"RATE_LIMIT_START_TIME={args.rate_limit_start_time}",
        "-e",
        f"RATE_LIMIT_ITERATIONS={args.rate_limit_iterations}",
    ]
    k6_run = run_command(k6_cmd)
    safe_stream_write(k6_run.stdout, stderr=False)
    safe_stream_write(k6_run.stderr, stderr=True)

    if k6_run.returncode != 0:
        detail = (k6_run.stderr or k6_run.stdout or "").strip()
        if result_json.exists() and result_json.stat().st_size > 0:
            write_result_meta(
                result_json,
                status="FAIL",
                reason_code=REASON_K6_EXECUTION_FAILED,
                reason_detail=_trim(detail) if detail else "k6 run returned non-zero exit code",
                remediation_hint="Inspect k6 output and backend logs, then rerun.",
                append=True,
            )
        else:
            write_result_meta(
                result_json,
                status="FAIL",
                reason_code=REASON_K6_EXECUTION_FAILED,
                reason_detail=_trim(detail) if detail else "k6 run returned non-zero exit code",
                remediation_hint="Inspect k6 output and backend logs, then rerun.",
                append=False,
            )
        gate_code = assert_and_sync(
            result_json=result_json,
            thresholds=thresholds,
            gate_txt=gate_txt,
            gate_json=gate_json,
            date_tag=date_tag,
        )
        return gate_code if gate_code != 0 else 1

    if not result_json.exists() or result_json.stat().st_size == 0:
        write_result_meta(
            result_json,
            status="FAIL",
            reason_code=REASON_RESULT_FILE_MISSING,
            reason_detail="k6 finished but result.json is missing or empty",
            remediation_hint="Check k6 --out path and file permissions.",
            append=False,
        )

    return assert_and_sync(
        result_json=result_json,
        thresholds=thresholds,
        gate_txt=gate_txt,
        gate_json=gate_json,
        date_tag=date_tag,
    )


if __name__ == "__main__":
    raise SystemExit(main())
