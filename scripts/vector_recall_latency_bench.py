#!/usr/bin/env python3
"""pgvector IVFFlat recall/latency benchmark (local reproducibility)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_METHOD = "docker-exec"
DEFAULT_COMPOSE_FILE = "infra/docker-compose.yml"
DEFAULT_COMPOSE_SERVICE = "postgres"
DEFAULT_DATABASE = "aichatbot"
DEFAULT_DB_USER = "aichatbot"
DEFAULT_DB_PASSWORD = "local-dev-only-password"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5432
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TOP_K = 10
DEFAULT_QUERY_COUNT = 30
DEFAULT_PROBES = (1, 2, 4, 8, 16, 32)
DEFAULT_SEED = 42
DEFAULT_MAX_RECALL_DROP = 0.03
DEFAULT_MAX_P95_REGRESSION_RATIO = 1.30
DEFAULT_ARTIFACT_DIR = "docs/review/mvp_verification_pack/artifacts"


@dataclass
class Violation:
    code: str
    message: str
    details: str


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def default_artifact_date() -> str:
    return utc_now().strftime("%Y%m%d")


def parse_probe_values(raw: str) -> list[int]:
    text = raw.strip()
    if not text:
        raise argparse.ArgumentTypeError("probe values must not be empty")
    values: list[int] = []
    for token in text.split(","):
        candidate = token.strip()
        if not candidate:
            raise argparse.ArgumentTypeError("probe values contain an empty token")
        try:
            probe = int(candidate)
        except ValueError as exc:  # pragma: no cover - argparse path
            raise argparse.ArgumentTypeError(f"probe value is not an integer: {candidate}") from exc
        if probe <= 0:
            raise argparse.ArgumentTypeError(f"probe value must be > 0: {candidate}")
        values.append(probe)
    unique = sorted(set(values))
    if not unique:
        raise argparse.ArgumentTypeError("probe values must not be empty")
    return unique


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark pgvector IVFFlat recall and latency deltas")
    parser.add_argument("--method", choices=("docker-exec", "local"), default=DEFAULT_METHOD)
    parser.add_argument("--compose-file", default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--compose-service", default=DEFAULT_COMPOSE_SERVICE)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--db-user", default=DEFAULT_DB_USER)
    parser.add_argument("--db-password", default=os.environ.get("DB_PASSWORD", DEFAULT_DB_PASSWORD))
    parser.add_argument("--host", default=os.environ.get("DB_HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DB_PORT", str(DEFAULT_PORT))))
    parser.add_argument("--tenant-id", default=DEFAULT_TENANT_ID)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--query-count", type=int, default=DEFAULT_QUERY_COUNT)
    parser.add_argument("--probe-values", type=parse_probe_values, default=list(DEFAULT_PROBES))
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--baseline-json")
    parser.add_argument("--max-recall-drop", type=float, default=DEFAULT_MAX_RECALL_DROP)
    parser.add_argument("--max-p95-regression-ratio", type=float, default=DEFAULT_MAX_P95_REGRESSION_RATIO)
    parser.add_argument("--artifact-dir", default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--artifact-date", default=default_artifact_date())
    parser.add_argument("--output-txt")
    parser.add_argument("--output-json")
    return parser.parse_args(argv)


def run_command(command: list[str], env: dict[str, str] | None = None) -> CommandResult:
    proc = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return CommandResult(returncode=proc.returncode, stdout=proc.stdout or "", stderr=proc.stderr or "")


def summarize_output(result: CommandResult, limit: int = 1400) -> str:
    merged = (result.stdout.strip() + "\n" + result.stderr.strip()).strip()
    if not merged:
        return "(no output)"
    if len(merged) <= limit:
        return merged
    return merged[: limit - 3] + "..."


def quote_sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def compose_base(compose_file: str) -> list[str]:
    return ["docker", "compose", "-f", compose_file]


def build_psql_command(args: argparse.Namespace, sql: str) -> tuple[list[str], dict[str, str]]:
    env = dict(os.environ)
    env["PGPASSWORD"] = args.db_password
    if args.method == "docker-exec":
        command = [
            *compose_base(args.compose_file),
            "exec",
            "-T",
            "-e",
            f"PGPASSWORD={args.db_password}",
            args.compose_service,
            "psql",
            "-U",
            args.db_user,
            "-d",
            args.database,
            "-X",
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
            "-F",
            "\t",
            "-c",
            sql,
        ]
        return command, env

    command = [
        "psql",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.db_user,
        "-d",
        args.database,
        "-X",
        "-q",
        "-v",
        "ON_ERROR_STOP=1",
        "-At",
        "-F",
        "\t",
        "-c",
        sql,
    ]
    return command, env


def run_sql(args: argparse.Namespace, sql: str) -> tuple[bool, str]:
    command, env = build_psql_command(args, sql)
    result = run_command(command, env=env)
    if result.returncode != 0:
        details = f"command={' '.join(command)}\n{summarize_output(result)}"
        return False, details
    return True, result.stdout.strip()


def last_non_empty_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def parse_id_list(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    return [token for token in text.split(",") if token]


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (len(sorted_values) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return float(sorted_values[low] + (sorted_values[high] - sorted_values[low]) * weight)


def render_text(payload: dict) -> str:
    lines = [
        "vector_recall_latency_bench",
        f"status={payload['status']}",
        f"method={payload['method']}",
        f"tenant_id={payload['tenant_id']}",
        f"row_count={payload['row_count_non_null_embedding']}",
        f"top_k={payload['top_k']}",
        f"query_count={payload['query_count']}",
        f"probe_values={','.join(str(item) for item in payload['probe_values'])}",
        f"probe_results={len(payload['probe_results'])}",
        f"violation_count={payload['violation_count']}",
    ]
    for result in payload["probe_results"]:
        lines.append(
            "probe="
            + str(result["probe"])
            + " recall_at_k="
            + f"{result['recall_at_k']:.6f}"
            + " p50_ms="
            + f"{result['p50_ms']:.3f}"
            + " p95_ms="
            + f"{result['p95_ms']:.3f}"
        )
    baseline = payload.get("baseline_comparison", {})
    if baseline:
        lines.append(f"baseline.enabled={baseline.get('enabled', False)}")
        if baseline.get("enabled"):
            lines.append(f"baseline.path={baseline.get('baseline_path', '')}")
            lines.append(f"baseline.status={baseline.get('status', 'UNKNOWN')}")
            lines.append(f"baseline.recall_drop={baseline.get('recall_drop', 0.0):.6f}")
            lines.append(f"baseline.p95_regression_ratio={baseline.get('p95_regression_ratio', 0.0):.6f}")
    for violation in payload["violations"]:
        lines.append(f"- [{violation['code']}] {violation['message']} :: {violation['details']}")
    return "\n".join(lines) + "\n"


def write_output(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def select_best_probe(probe_results: list[dict]) -> dict | None:
    if not probe_results:
        return None
    ordered = sorted(
        probe_results,
        key=lambda item: (-float(item["recall_at_k"]), float(item["p95_ms"]), int(item["probe"])),
    )
    return ordered[0]


def check_positive(name: str, value: int, violations: list[Violation]) -> None:
    if value <= 0:
        violations.append(
            Violation(
                code="BENCH_ARGUMENT_INVALID",
                message=f"{name} must be > 0",
                details=f"{name}={value}",
            )
        )


def run_scalar_int(args: argparse.Namespace, sql: str) -> tuple[bool, int, str]:
    ok, output = run_sql(args, sql)
    if not ok:
        return False, -1, output
    line = last_non_empty_line(output)
    try:
        return True, int(line), ""
    except ValueError:
        return False, -1, f"non-integer scalar result: {line!r}"


def evaluate_baseline(
    payload: dict,
    baseline_path: Path | None,
    max_recall_drop: float,
    max_p95_regression_ratio: float,
    violations: list[Violation],
) -> dict:
    comparison = {
        "enabled": baseline_path is not None,
        "baseline_path": baseline_path.as_posix() if baseline_path else "",
        "max_recall_drop": max_recall_drop,
        "max_p95_regression_ratio": max_p95_regression_ratio,
        "status": "SKIPPED",
    }
    if baseline_path is None:
        return comparison

    try:
        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception as exc:
        violations.append(
            Violation(
                code="BENCH_BASELINE_INVALID",
                message="failed to parse baseline json",
                details=str(exc),
            )
        )
        comparison["status"] = "FAIL"
        return comparison

    baseline_best = baseline_payload.get("best_probe")
    if not isinstance(baseline_best, dict):
        baseline_best = select_best_probe(list(baseline_payload.get("probe_results", [])))
    current_best = payload.get("best_probe")
    comparison["current_best_probe"] = current_best
    comparison["baseline_best_probe"] = baseline_best

    if not current_best or not baseline_best:
        violations.append(
            Violation(
                code="BENCH_BASELINE_INVALID",
                message="baseline/current best_probe is missing",
                details="ensure probe_results and best_probe exist in baseline and current run",
            )
        )
        comparison["status"] = "FAIL"
        return comparison

    baseline_recall = float(baseline_best.get("recall_at_k", 0.0))
    baseline_p95 = float(baseline_best.get("p95_ms", 0.0))
    current_recall = float(current_best.get("recall_at_k", 0.0))
    current_p95 = float(current_best.get("p95_ms", 0.0))

    if baseline_p95 <= 0:
        violations.append(
            Violation(
                code="BENCH_BASELINE_INVALID",
                message="baseline p95_ms must be > 0",
                details=f"baseline_p95={baseline_p95}",
            )
        )
        comparison["status"] = "FAIL"
        return comparison

    recall_drop = baseline_recall - current_recall
    p95_ratio = current_p95 / baseline_p95
    comparison["recall_drop"] = recall_drop
    comparison["p95_regression_ratio"] = p95_ratio

    if recall_drop > max_recall_drop:
        violations.append(
            Violation(
                code="BENCH_RECALL_REGRESSION",
                message="recall@k regression exceeds allowed drop",
                details=f"drop={recall_drop:.6f} threshold={max_recall_drop:.6f}",
            )
        )

    if p95_ratio > max_p95_regression_ratio:
        violations.append(
            Violation(
                code="BENCH_LATENCY_REGRESSION",
                message="p95 latency regression exceeds allowed ratio",
                details=f"ratio={p95_ratio:.6f} threshold={max_p95_regression_ratio:.6f}",
            )
        )

    comparison["status"] = "PASS" if not any(
        item.code in {"BENCH_RECALL_REGRESSION", "BENCH_LATENCY_REGRESSION", "BENCH_BASELINE_INVALID"}
        for item in violations
    ) else "FAIL"
    return comparison


def run_benchmark(args: argparse.Namespace) -> dict:
    started_at = utc_now()
    started_mono = time.monotonic()

    violations: list[Violation] = []
    probe_results: list[dict] = []

    check_positive("top_k", args.top_k, violations)
    check_positive("query_count", args.query_count, violations)
    if args.method == "docker-exec":
        compose_path = Path(args.compose_file)
        if not compose_path.exists():
            violations.append(
                Violation(
                    code="COMPOSE_FILE_MISSING",
                    message="compose file does not exist",
                    details=compose_path.as_posix(),
                )
            )

    tenant_literal = quote_sql_literal(args.tenant_id)
    seed_literal = quote_sql_literal(str(args.seed))
    dataset_filter = (
        "FROM tb_kb_chunk_embedding e "
        "JOIN tb_kb_chunk c ON c.id = e.chunk_id AND c.tenant_id = e.tenant_id "
        "JOIN tb_kb_document_version dv ON dv.id = c.document_version_id AND dv.tenant_id = c.tenant_id "
        f"WHERE e.tenant_id = {tenant_literal} "
        "AND e.embedding_vector_1536 IS NOT NULL "
        "AND dv.status = 'approved'"
    )

    row_count = 0
    query_ids: list[str] = []

    if not violations:
        ok, row_count, details = run_scalar_int(
            args,
            f"SELECT COUNT(*) {dataset_filter};",
        )
        if not ok:
            violations.append(
                Violation(
                    code="BENCH_QUERY_FAILED",
                    message="failed to count eligible vector rows",
                    details=details,
                )
            )

    if not violations:
        required_rows = max(args.top_k, args.query_count)
        if row_count < required_rows:
            violations.append(
                Violation(
                    code="BENCH_DATA_INSUFFICIENT",
                    message="insufficient eligible rows for benchmark",
                    details=f"row_count={row_count} required={required_rows}",
                )
            )

    if not violations:
        sample_sql = (
            "SELECT e.id::text "
            f"{dataset_filter} "
            f"ORDER BY md5(e.id::text || {seed_literal}) "
            f"LIMIT {args.query_count};"
        )
        ok, output_full = run_sql(args, sample_sql)
        if not ok:
            violations.append(
                Violation(
                    code="BENCH_QUERY_FAILED",
                    message="failed to sample query vectors",
                    details=output_full,
                )
            )
        else:
            query_ids = [line.strip() for line in output_full.splitlines() if line.strip()]
            if len(query_ids) != args.query_count:
                violations.append(
                    Violation(
                        code="BENCH_DATA_INSUFFICIENT",
                        message="sampled query id count is smaller than requested",
                        details=f"sampled={len(query_ids)} requested={args.query_count}",
                    )
                )

    for probe in args.probe_values:
        if violations:
            break
        per_query_recalls: list[float] = []
        per_query_latency_ms: list[float] = []
        for query_id in query_ids:
            query_id_literal = quote_sql_literal(query_id)

            exact_sql = (
                "BEGIN; "
                "SET LOCAL enable_indexscan = off; "
                "SET LOCAL enable_bitmapscan = off; "
                "WITH probe AS ("
                "  SELECT embedding_vector_1536 AS qv "
                "  FROM tb_kb_chunk_embedding "
                f"  WHERE tenant_id = {tenant_literal} "
                f"    AND id = {query_id_literal} "
                "    AND embedding_vector_1536 IS NOT NULL"
                "), ranked AS ("
                "  SELECT e.id::text AS id "
                f"  {dataset_filter} "
                "  ORDER BY e.embedding_vector_1536 <=> (SELECT qv FROM probe) "
                f"  LIMIT {args.top_k}"
                ") "
                "SELECT COALESCE(string_agg(id, ',' ORDER BY id), '') FROM ranked; "
                "ROLLBACK;"
            )
            ok, exact_out = run_sql(args, exact_sql)
            if not ok:
                violations.append(
                    Violation(
                        code="BENCH_QUERY_FAILED",
                        message="exact top-k query failed",
                        details=exact_out,
                    )
                )
                break
            exact_ids = parse_id_list(last_non_empty_line(exact_out))

            approx_sql = (
                "BEGIN; "
                f"SET LOCAL ivfflat.probes = {probe}; "
                "WITH probe AS ("
                "  SELECT embedding_vector_1536 AS qv "
                "  FROM tb_kb_chunk_embedding "
                f"  WHERE tenant_id = {tenant_literal} "
                f"    AND id = {query_id_literal} "
                "    AND embedding_vector_1536 IS NOT NULL"
                "), started AS ("
                "  SELECT clock_timestamp() AS t0"
                "), ranked AS ("
                "  SELECT e.id::text AS id "
                f"  {dataset_filter} "
                "  ORDER BY e.embedding_vector_1536 <=> (SELECT qv FROM probe) "
                f"  LIMIT {args.top_k}"
                "), elapsed AS ("
                "  SELECT EXTRACT(EPOCH FROM (clock_timestamp() - (SELECT t0 FROM started))) * 1000.0 AS latency_ms "
                "  FROM (SELECT COUNT(*) FROM ranked) AS _used"
                ") "
                "SELECT COALESCE((SELECT string_agg(id, ',' ORDER BY id) FROM ranked), '') "
                "       || E'\\t' || "
                "       COALESCE((SELECT latency_ms::text FROM elapsed), '0'); "
                "ROLLBACK;"
            )
            ok, approx_out = run_sql(args, approx_sql)
            if not ok:
                violations.append(
                    Violation(
                        code="BENCH_QUERY_FAILED",
                        message="approx top-k query failed",
                        details=approx_out,
                    )
                )
                break

            approx_line = last_non_empty_line(approx_out)
            if "\t" not in approx_line:
                violations.append(
                    Violation(
                        code="BENCH_QUERY_PARSE_FAILED",
                        message="approx query output missing latency field",
                        details=approx_line,
                    )
                )
                break
            approx_ids_raw, latency_raw = approx_line.split("\t", 1)
            approx_ids = parse_id_list(approx_ids_raw)
            try:
                latency_ms = float(latency_raw)
            except ValueError:
                violations.append(
                    Violation(
                        code="BENCH_QUERY_PARSE_FAILED",
                        message="failed to parse approx latency",
                        details=latency_raw,
                    )
                )
                break

            if len(exact_ids) < args.top_k or len(approx_ids) < args.top_k:
                violations.append(
                    Violation(
                        code="BENCH_TOPK_RESULT_SHORT",
                        message="top-k result is smaller than requested size",
                        details=f"probe={probe} query_id={query_id} exact={len(exact_ids)} approx={len(approx_ids)} top_k={args.top_k}",
                    )
                )
                break

            overlap = len(set(exact_ids) & set(approx_ids))
            per_query_recalls.append(overlap / float(args.top_k))
            per_query_latency_ms.append(latency_ms)

        if violations:
            break

        probe_results.append(
            {
                "probe": probe,
                "query_count": len(per_query_recalls),
                "recall_at_k": statistics.fmean(per_query_recalls) if per_query_recalls else 0.0,
                "p50_ms": percentile(per_query_latency_ms, 50.0),
                "p95_ms": percentile(per_query_latency_ms, 95.0),
                "avg_ms": statistics.fmean(per_query_latency_ms) if per_query_latency_ms else 0.0,
            }
        )

    best_probe = select_best_probe(probe_results)
    baseline_path = Path(args.baseline_json) if args.baseline_json else None
    baseline_comparison = evaluate_baseline(
        payload={"probe_results": probe_results, "best_probe": best_probe},
        baseline_path=baseline_path,
        max_recall_drop=args.max_recall_drop,
        max_p95_regression_ratio=args.max_p95_regression_ratio,
        violations=violations,
    )

    finished_at = utc_now()
    payload = {
        "status": "PASS" if not violations else "FAIL",
        "started_at_utc": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at_utc": finished_at.isoformat().replace("+00:00", "Z"),
        "duration_ms": int((time.monotonic() - started_mono) * 1000),
        "method": args.method,
        "compose_file": args.compose_file,
        "compose_service": args.compose_service,
        "database": args.database,
        "db_user": args.db_user,
        "tenant_id": args.tenant_id,
        "top_k": args.top_k,
        "query_count": args.query_count,
        "probe_values": args.probe_values,
        "seed": args.seed,
        "row_count_non_null_embedding": row_count,
        "query_ids": query_ids,
        "probe_results": probe_results,
        "best_probe": best_probe,
        "baseline_comparison": baseline_comparison,
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    artifact_dir = Path(args.artifact_dir)
    output_txt = (
        Path(args.output_txt)
        if args.output_txt
        else artifact_dir / f"vector_recall_latency_bench_{args.artifact_date}.txt"
    )
    output_json = (
        Path(args.output_json)
        if args.output_json
        else artifact_dir / f"vector_recall_latency_bench_{args.artifact_date}.json"
    )

    payload = run_benchmark(args)
    text_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    write_output(output_txt, text_report)
    write_output(output_json, json_report)

    sys.stdout.write(text_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
