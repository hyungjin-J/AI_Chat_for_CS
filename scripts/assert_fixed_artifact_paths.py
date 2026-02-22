#!/usr/bin/env python3
"""Assert fixed artifact paths contract to prevent rename drift."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath


@dataclass
class Violation:
    code: str
    path: str
    message: str
    remediation: str


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="strict"))


def normalize(path: str) -> str:
    return path.replace("\\", "/").strip()


def has_path_traversal(path: str) -> bool:
    return ".." in PurePosixPath(path).parts


def run_contract_check(contract_path: Path) -> tuple[dict, list[Violation]]:
    contract = load_contract(contract_path)
    artifact_root = normalize(contract.get("artifact_root", ""))
    allowed_non_artifact = {normalize(item) for item in contract.get("allowed_non_artifact_paths", [])}
    fixed_paths = [normalize(item) for item in contract.get("fixed_paths", [])]

    violations: list[Violation] = []

    for raw_path in fixed_paths:
        if not raw_path:
            violations.append(
                Violation(
                    code="PATH_EMPTY",
                    path=raw_path,
                    message="empty path entry in contract",
                    remediation="Remove empty entry from scripts/contracts/fixed_artifact_paths.json",
                )
            )
            continue

        if raw_path.startswith(("http://", "https://")):
            violations.append(
                Violation(
                    code="PATH_REMOTE_NOT_ALLOWED",
                    path=raw_path,
                    message="contract paths must be repository-local, remote URL found",
                    remediation="Replace remote URL with repository-local evidence path.",
                )
            )
            continue

        if has_path_traversal(raw_path):
            violations.append(
                Violation(
                    code="PATH_TRAVERSAL_FORBIDDEN",
                    path=raw_path,
                    message="path traversal '..' is forbidden in fixed artifact contract",
                    remediation="Use normalized repository-relative paths only.",
                )
            )
            continue

        in_allowed_non_artifact = raw_path in allowed_non_artifact
        in_artifact_root = raw_path.startswith(artifact_root)

        if not in_allowed_non_artifact and not in_artifact_root:
            violations.append(
                Violation(
                    code="PATH_OUT_OF_SCOPE",
                    path=raw_path,
                    message="path must be under artifacts root or explicitly allowlisted",
                    remediation=(
                        "Move evidence under artifacts root or add it to "
                        "'allowed_non_artifact_paths' with review."
                    ),
                )
            )
            continue

        file_path = Path(raw_path)
        if not file_path.exists():
            violations.append(
                Violation(
                    code="PATH_MISSING",
                    path=raw_path,
                    message="required fixed path does not exist",
                    remediation=(
                        f"Recreate or restore {raw_path} by rerunning its gate/script, "
                        "then commit the file."
                    ),
                )
            )

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "contract_path": contract_path.as_posix(),
        "artifact_root": artifact_root,
        "allowed_non_artifact_paths": sorted(allowed_non_artifact),
        "fixed_paths_count": len(fixed_paths),
        "violation_count": len(violations),
        "violations": [asdict(v) for v in violations],
    }
    return payload, violations


def render_text_report(payload: dict) -> str:
    lines = [
        "fixed_artifact_paths_contract",
        f"status={payload['status']}",
        f"contract_path={payload['contract_path']}",
        f"artifact_root={payload['artifact_root']}",
        f"fixed_paths_count={payload['fixed_paths_count']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(
            f"- [{item['code']}] path={item['path']} message={item['message']} "
            f"remediation={item['remediation']}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert fixed artifact paths contract")
    parser.add_argument(
        "--contract",
        default="scripts/contracts/fixed_artifact_paths.json",
        help="Path to fixed artifact paths contract JSON",
    )
    parser.add_argument("--output-txt", help="Optional text output report path")
    parser.add_argument("--output-json", help="Optional JSON output report path")
    args = parser.parse_args()

    contract_path = Path(args.contract)
    if not contract_path.exists():
        message = (
            f"fixed_artifact_paths_contract\n"
            f"status=FAIL\n"
            f"violation_count=1\n"
            f"- [CONTRACT_MISSING] path={contract_path.as_posix()} "
            "message=contract file not found remediation=Restore scripts/contracts/fixed_artifact_paths.json\n"
        )
        if args.output_txt:
            out_txt = Path(args.output_txt)
            out_txt.parent.mkdir(parents=True, exist_ok=True)
            out_txt.write_text(message, encoding="utf-8")
        if args.output_json:
            out_json = Path(args.output_json)
            out_json.parent.mkdir(parents=True, exist_ok=True)
            out_json.write_text(
                json.dumps(
                    {
                        "status": "FAIL",
                        "contract_path": contract_path.as_posix(),
                        "violation_count": 1,
                        "violations": [
                            {
                                "code": "CONTRACT_MISSING",
                                "path": contract_path.as_posix(),
                                "message": "contract file not found",
                                "remediation": "Restore scripts/contracts/fixed_artifact_paths.json",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        sys.stdout.write(message)
        return 1

    payload, violations = run_contract_check(contract_path=contract_path)
    report_text = render_text_report(payload)
    report_json = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(report_text, encoding="utf-8")
    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(report_json, encoding="utf-8")

    sys.stdout.write(report_text)
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
