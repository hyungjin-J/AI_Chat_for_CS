import json
import os
import subprocess
import sys
import time
from pathlib import Path


ARTIFACT_DIR = Path("docs/review/mvp_verification_pack/artifacts")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = ARTIFACT_DIR / "sse_resume_fault_injection.log"
BACKEND_LOG = ARTIFACT_DIR / "sse_resume_fault_backend.log"


def run_cmd(command: str) -> str:
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"command failed: {command}\nstdout={completed.stdout}\nstderr={completed.stderr}")
    return completed.stdout.strip()


def wait_backend_ready(timeout_sec: int = 90) -> None:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            run_cmd(
                'curl -sS http://localhost:8080/health '
                '-H "X-Tenant-Key: demo-tenant" -H "X-Trace-Id: 11111111-1111-4111-8111-111111111111"'
            )
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("backend_not_ready")


def curl_json(url: str, headers: list[str], body: dict | None = None) -> dict:
    body_arg = ""
    if body is not None:
        payload = json.dumps(body).replace('"', '\\"')
        body_arg = f' -H "Content-Type: application/json" --data "{payload}"'
    header_args = " ".join([f'-H "{h}"' for h in headers])
    out = run_cmd(f'curl -sS {url} {header_args}{body_arg}')
    return json.loads(out)


def curl_sse(url: str, headers: list[str]) -> str:
    header_args = " ".join([f'-H "{h}"' for h in headers])
    command = f'curl -sS -N {url} {header_args}'
    completed = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    # curl 18 can happen on SSE when server closes stream after done.
    if completed.returncode not in (0, 18):
        raise RuntimeError(
            f"command failed: {command}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed.stdout.strip()


def parse_sse_text(raw: str) -> list[dict]:
    events = []
    current = {"id": None, "event": None, "data": []}
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("id:"):
            current["id"] = line[3:].strip()
        elif line.startswith("event:"):
            current["event"] = line[6:].strip()
        elif line.startswith("data:"):
            current["data"].append(line[5:].strip())
        elif line == "":
            if current["event"] is not None:
                events.append(
                    {
                        "id": current["id"],
                        "event": current["event"],
                        "data": "\n".join(current["data"]),
                    }
                )
            current = {"id": None, "event": None, "data": []}
    return events


def event_ids(events: list[dict]) -> list[int]:
    return [int(e["id"]) for e in events if e.get("id")]


def main() -> int:
    backend_proc = None
    lines: list[str] = []
    try:
        run_cmd("docker compose -f infra/docker-compose.yml up -d")

        env = os.environ.copy()
        env["SPRING_PROFILES_ACTIVE"] = "postgres"
        env["APP_LLM_PROVIDER"] = "mock"
        env["DB_URL"] = "jdbc:postgresql://localhost:5432/aichatbot"
        env["DB_USERNAME"] = "aichatbot"
        env["DB_PASSWORD"] = "local-dev-only-password"
        env["APP_BUDGET_SSE_CONCURRENCY_MAX_PER_USER"] = "10"

        with BACKEND_LOG.open("w", encoding="utf-8") as backend_out:
            backend_proc = subprocess.Popen(
                ["cmd", "/c", "cd /d backend && gradlew.bat bootRun --no-daemon"],
                stdout=backend_out,
                stderr=subprocess.STDOUT,
                env=env,
            )

        wait_backend_ready()

        login = curl_json(
            "http://localhost:8080/v1/auth/login",
            [
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 11111111-1111-4111-8111-111111111111",
                "Idempotency-Key: idem-sse-net-login-1",
            ],
            {"login_id": "agent1", "password": "agent1-pass", "channel_id": "test", "client_nonce": "net-1"},
        )
        token = login["access_token"]

        session = curl_json(
            "http://localhost:8080/v1/sessions",
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 22222222-2222-4222-8222-222222222222",
                "Idempotency-Key: idem-sse-net-session-1",
            ],
            {},
        )
        session_id = session["session_id"]

        message = curl_json(
            f"http://localhost:8080/v1/sessions/{session_id}/messages",
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 33333333-3333-4333-8333-333333333333",
                "Idempotency-Key: idem-sse-net-message-1",
            ],
            {"text": "refund policy", "top_k": 3, "client_nonce": "net-msg-1"},
        )
        message_id = message["id"]
        stream_url = f"http://localhost:8080/v1/sessions/{session_id}/messages/{message_id}/stream"

        baseline_raw = curl_sse(
            stream_url,
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 44444444-4444-4444-8444-444444444444",
            ],
        )
        baseline_events = parse_sse_text(baseline_raw)
        baseline_ids = event_ids(baseline_events)
        if len(baseline_ids) < 5:
            raise RuntimeError(f"baseline_too_short ids={baseline_ids}")

        mid_1 = baseline_ids[2]
        resume_1_raw = curl_sse(
            f"http://localhost:8080/v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id={mid_1}",
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 55555555-5555-4555-8555-555555555555",
            ],
        )
        resume_1_events = parse_sse_text(resume_1_raw)
        resume_1_ids = event_ids(resume_1_events)
        expected_1 = [i for i in baseline_ids if i > mid_1]
        if resume_1_ids != expected_1:
            raise RuntimeError(f"resume_1_mismatch ids={resume_1_ids} expected={expected_1}")

        mid_2 = baseline_ids[1]
        resume_2_raw = curl_sse(
            f"http://localhost:8080/v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id={mid_2}",
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 66666666-6666-4666-8666-666666666666",
            ],
        )
        resume_2_events = parse_sse_text(resume_2_raw)
        resume_2_ids = event_ids(resume_2_events)
        expected_2 = [i for i in baseline_ids if i > mid_2]
        if resume_2_ids != expected_2:
            raise RuntimeError(f"resume_2_mismatch ids={resume_2_ids} expected={expected_2}")

        past_raw = curl_sse(
            f"http://localhost:8080/v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id=0",
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 77777777-7777-4777-8777-777777777777",
            ],
        )
        past_events = parse_sse_text(past_raw)
        past_ids = event_ids(past_events)
        if past_ids not in [baseline_ids, [i for i in baseline_ids if i > 0]]:
            raise RuntimeError(f"past_resume_mismatch ids={past_ids} baseline={baseline_ids}")

        future_raw = curl_sse(
            f"http://localhost:8080/v1/sessions/{session_id}/messages/{message_id}/stream/resume?last_event_id=999",
            [
                f"Authorization: Bearer {token}",
                "X-Tenant-Key: demo-tenant",
                "X-Trace-Id: 88888888-8888-4888-8888-888888888888",
            ],
        )
        future_events = parse_sse_text(future_raw)
        future_ids = event_ids(future_events)
        if future_ids and any(i <= baseline_ids[-1] for i in future_ids):
            raise RuntimeError(f"future_resume_replayed_old ids={future_ids}")

        lines.append(f"baseline_ids={baseline_ids}")
        lines.append(f"resume_1_ids={resume_1_ids}")
        lines.append(f"resume_2_ids={resume_2_ids}")
        lines.append(f"past_resume_ids={past_ids}")
        lines.append(f"future_resume_ids={future_ids}")
        lines.append("assertion_result=PASS")

        with LOG_PATH.open("w", encoding="utf-8") as fp:
            fp.write("\n".join(lines))
            fp.write("\n\n[baseline_events]\n")
            fp.write(json.dumps(baseline_events, ensure_ascii=False, indent=2))
            fp.write("\n\n[resume_1_events]\n")
            fp.write(json.dumps(resume_1_events, ensure_ascii=False, indent=2))
            fp.write("\n\n[resume_2_events]\n")
            fp.write(json.dumps(resume_2_events, ensure_ascii=False, indent=2))
            fp.write("\n\n[past_resume_events]\n")
            fp.write(json.dumps(past_events, ensure_ascii=False, indent=2))
            fp.write("\n\n[future_resume_events]\n")
            fp.write(json.dumps(future_events, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        with LOG_PATH.open("w", encoding="utf-8") as fp:
            fp.write("assertion_result=FAIL\n")
            fp.write(f"error={exc}\n")
        return 1
    finally:
        if backend_proc and backend_proc.poll() is None:
            backend_proc.kill()
        try:
            run_cmd(
                'powershell -Command "Get-NetTCPConnection -LocalPort 8080 -State Listen | '
                'Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }"'
            )
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
