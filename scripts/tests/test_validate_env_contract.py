from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "validate_env_contract.py"


def run_validator(env_example: Path, output_json: Path, output_txt: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python",
            str(SCRIPT),
            "--env-example",
            str(env_example),
            "--output-json",
            str(output_json),
            "--output-txt",
            str(output_txt),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


class ValidateEnvContractTest(unittest.TestCase):
    def test_passes_with_redacted_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            env_file = tmp_dir / ".env.example"
            out_json = tmp_dir / "out.json"
            out_txt = tmp_dir / "out.txt"
            env_file.write_text(
                "\n".join(
                    [
                        "POSTGRES_DB=<REDACTED>",
                        "POSTGRES_USER=<REDACTED>",
                        "POSTGRES_PASSWORD=<REDACTED>",
                        "DB_URL=<REDACTED>",
                        "DB_USERNAME=<REDACTED>",
                        "DB_PASSWORD=<REDACTED>",
                        "REDIS_HOST=redis",
                        "REDIS_PORT=6379",
                        "SPRING_PROFILES_ACTIVE=postgres",
                        "APP_LLM_PROVIDER=ollama",
                        "APP_IDEMPOTENCY_STORE=redis",
                        "APP_IDEMPOTENCY_REDIS_FAIL_STRATEGY=fail_closed",
                        "APP_TRACE_REQUIRE_HEADER=true",
                        "APP_OLLAMA_BASE_URL=http://ollama:11434",
                        "APP_OLLAMA_MODEL=qwen2.5:3b-instruct",
                        "LLM_PROVIDER_KEY_REF=secret://<REDACTED>",
                        "VITE_API_BASE_URL=http://backend:8080",
                        "APP_JWT_SECRET=<REDACTED>",
                        "APP_JWT_SECRET_REF=secret://<REDACTED>",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            completed = run_validator(env_file, out_json, out_txt)
            self.assertEqual(completed.returncode, 0, msg=completed.stdout + completed.stderr)

            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(payload["violation_count"], 0)

    def test_fails_when_tenant_default_is_defined(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            env_file = tmp_dir / ".env.example"
            out_json = tmp_dir / "out.json"
            out_txt = tmp_dir / "out.txt"
            env_file.write_text(
                "\n".join(
                    [
                        "POSTGRES_DB=<REDACTED>",
                        "POSTGRES_USER=<REDACTED>",
                        "POSTGRES_PASSWORD=<REDACTED>",
                        "DB_URL=<REDACTED>",
                        "DB_USERNAME=<REDACTED>",
                        "DB_PASSWORD=<REDACTED>",
                        "REDIS_HOST=redis",
                        "REDIS_PORT=6379",
                        "SPRING_PROFILES_ACTIVE=postgres",
                        "APP_LLM_PROVIDER=ollama",
                        "APP_IDEMPOTENCY_STORE=redis",
                        "APP_IDEMPOTENCY_REDIS_FAIL_STRATEGY=fail_closed",
                        "APP_TRACE_REQUIRE_HEADER=true",
                        "APP_OLLAMA_BASE_URL=http://ollama:11434",
                        "APP_OLLAMA_MODEL=qwen2.5:3b-instruct",
                        "LLM_PROVIDER_KEY_REF=secret://<REDACTED>",
                        "VITE_API_BASE_URL=http://backend:8080",
                        "APP_JWT_SECRET=<REDACTED>",
                        "APP_JWT_SECRET_REF=secret://<REDACTED>",
                        "X_TENANT_KEY=demo-tenant",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            completed = run_validator(env_file, out_json, out_txt)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("TENANT_DEFAULT_FORBIDDEN", completed.stdout)

    def test_fails_when_secret_ref_is_not_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            env_file = tmp_dir / ".env.example"
            out_json = tmp_dir / "out.json"
            out_txt = tmp_dir / "out.txt"
            env_file.write_text(
                "\n".join(
                    [
                        "POSTGRES_DB=<REDACTED>",
                        "POSTGRES_USER=<REDACTED>",
                        "POSTGRES_PASSWORD=<REDACTED>",
                        "DB_URL=<REDACTED>",
                        "DB_USERNAME=<REDACTED>",
                        "DB_PASSWORD=<REDACTED>",
                        "REDIS_HOST=redis",
                        "REDIS_PORT=6379",
                        "SPRING_PROFILES_ACTIVE=postgres",
                        "APP_LLM_PROVIDER=ollama",
                        "APP_IDEMPOTENCY_STORE=redis",
                        "APP_IDEMPOTENCY_REDIS_FAIL_STRATEGY=fail_closed",
                        "APP_TRACE_REQUIRE_HEADER=true",
                        "APP_OLLAMA_BASE_URL=http://ollama:11434",
                        "APP_OLLAMA_MODEL=qwen2.5:3b-instruct",
                        "LLM_PROVIDER_KEY_REF=secret://provider/live-key",
                        "VITE_API_BASE_URL=http://backend:8080",
                        "APP_JWT_SECRET=<REDACTED>",
                        "APP_JWT_SECRET_REF=secret://<REDACTED>",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            completed = run_validator(env_file, out_json, out_txt)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("SECRET_REF_REDACTION_REQUIRED", completed.stdout)


if __name__ == "__main__":
    unittest.main()
