#!/usr/bin/env python3
"""Validate MyBatis mapper namespace drift against Java mapper interfaces."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


PACKAGE_PATTERN = re.compile(r"^\s*package\s+([A-Za-z0-9_.]+)\s*;\s*$")


@dataclass
class Violation:
    code: str
    file: str
    detail: str


def load_contract(root: Path, contract_path: str) -> dict:
    path = Path(contract_path)
    resolved = path if path.is_absolute() else root / path
    return json.loads(resolved.read_text(encoding="utf-8", errors="strict"))


def extract_fqcn(java_file: Path) -> str:
    package_name: str | None = None
    for line in java_file.read_text(encoding="utf-8", errors="strict").splitlines():
        match = PACKAGE_PATTERN.match(line)
        if match:
            package_name = match.group(1)
            break
    if package_name is None:
        raise ValueError(f"package declaration not found: {java_file.as_posix()}")
    return f"{package_name}.{java_file.stem}"


def build_mapper_index(root: Path, contract: dict) -> tuple[dict[str, str], list[Violation]]:
    java_root = root / contract["java_root"]
    mapper_glob = contract["mapper_interface_glob"]
    mapper_map: dict[str, str] = {}
    violations: list[Violation] = []

    for java_file in sorted(java_root.glob(mapper_glob)):
        if not java_file.is_file():
            continue
        try:
            fqcn = extract_fqcn(java_file)
        except ValueError as error:
            violations.append(
                Violation(
                    code="MAPPER_PACKAGE_MISSING",
                    file=java_file.relative_to(root).as_posix(),
                    detail=str(error),
                )
            )
            continue
        if fqcn in mapper_map:
            violations.append(
                Violation(
                    code="MAPPER_FQCN_DUPLICATED",
                    file=java_file.relative_to(root).as_posix(),
                    detail=f"duplicate mapper fqcn: {fqcn}",
                )
            )
            continue
        mapper_map[fqcn] = java_file.relative_to(root).as_posix()
    return mapper_map, violations


def expected_context(namespace: str, namespace_context_map: dict[str, str]) -> str | None:
    for prefix, context in namespace_context_map.items():
        if namespace.startswith(prefix):
            return context
    return None


def parse_mapper_xml(xml_path: Path) -> str | None:
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return None
    root = tree.getroot()
    if root.tag != "mapper":
        return None
    namespace = root.attrib.get("namespace", "").strip()
    return namespace or None


def validate_xml_files(root: Path, contract: dict, mapper_index: dict[str, str]) -> tuple[dict[str, str], list[Violation]]:
    xml_root = root / contract["xml_root"]
    allowed_contexts = set(contract["allowed_xml_contexts"])
    namespace_context_map = contract["namespace_context_map"]
    legacy_prefixes = contract["legacy_namespace_prefixes"]

    namespace_to_xml: dict[str, str] = {}
    violations: list[Violation] = []

    for xml_file in sorted(xml_root.rglob("*.xml")):
        rel = xml_file.relative_to(root).as_posix()
        namespace = parse_mapper_xml(xml_file)
        if not namespace:
            violations.append(
                Violation(
                    code="NAMESPACE_MISSING",
                    file=rel,
                    detail="mapper namespace missing or XML parse error",
                )
            )
            continue

        if namespace in namespace_to_xml:
            violations.append(
                Violation(
                    code="NAMESPACE_DUPLICATED",
                    file=rel,
                    detail=f"{namespace} already declared in {namespace_to_xml[namespace]}",
                )
            )
            continue
        namespace_to_xml[namespace] = rel

        for legacy in legacy_prefixes:
            if namespace.startswith(legacy):
                violations.append(
                    Violation(
                        code="LEGACY_NAMESPACE_FORBIDDEN",
                        file=rel,
                        detail=namespace,
                    )
                )
                break

        if namespace not in mapper_index:
            violations.append(
                Violation(
                    code="NAMESPACE_WITHOUT_MAPPER_INTERFACE",
                    file=rel,
                    detail=namespace,
                )
            )

        parts = Path(rel).parts
        # .../mappers/<context>/file.xml
        try:
            context_index = parts.index("mappers") + 1
            xml_context = parts[context_index]
        except (ValueError, IndexError):
            xml_context = ""
        if xml_context not in allowed_contexts:
            violations.append(
                Violation(
                    code="XML_CONTEXT_FORBIDDEN",
                    file=rel,
                    detail=xml_context,
                )
            )
            continue

        inferred = expected_context(namespace=namespace, namespace_context_map=namespace_context_map)
        if inferred is None:
            violations.append(
                Violation(
                    code="NAMESPACE_CONTEXT_UNKNOWN",
                    file=rel,
                    detail=namespace,
                )
            )
            continue
        if inferred != xml_context:
            violations.append(
                Violation(
                    code="XML_PATH_NAMESPACE_CONTEXT_MISMATCH",
                    file=rel,
                    detail=f"path={xml_context}, namespace={inferred}, fqcn={namespace}",
                )
            )

    return namespace_to_xml, violations


def validate_mapper_coverage(
    mapper_index: dict[str, str],
    namespace_to_xml: dict[str, str],
) -> list[Violation]:
    violations: list[Violation] = []
    for namespace, java_rel in sorted(mapper_index.items()):
        if namespace not in namespace_to_xml:
            violations.append(
                Violation(
                    code="MAPPER_INTERFACE_WITHOUT_XML",
                    file=java_rel,
                    detail=namespace,
                )
            )
    return violations


def render_text(payload: dict) -> str:
    lines = [
        "verify_mapper_namespaces",
        f"status={payload['status']}",
        f"mapper_interface_count={payload['mapper_interface_count']}",
        f"xml_mapper_count={payload['xml_mapper_count']}",
        f"violation_count={payload['violation_count']}",
    ]
    for item in payload["violations"]:
        lines.append(f"- [{item['code']}] file={item['file']} detail={item['detail']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify MyBatis mapper namespace drift")
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract", default="scripts/contracts/mapper_namespace_contract.json")
    parser.add_argument("--output-json")
    parser.add_argument("--output-txt")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    contract = load_contract(root=root, contract_path=args.contract)

    mapper_index, mapper_violations = build_mapper_index(root=root, contract=contract)
    namespace_to_xml, xml_violations = validate_xml_files(root=root, contract=contract, mapper_index=mapper_index)
    coverage_violations = validate_mapper_coverage(mapper_index=mapper_index, namespace_to_xml=namespace_to_xml)
    violations = mapper_violations + xml_violations + coverage_violations

    payload = {
        "status": "PASS" if not violations else "FAIL",
        "mapper_interface_count": len(mapper_index),
        "xml_mapper_count": len(namespace_to_xml),
        "violation_count": len(violations),
        "violations": [asdict(item) for item in violations],
    }
    txt_report = render_text(payload)
    json_report = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.output_txt:
        out_txt = Path(args.output_txt)
        out_txt.parent.mkdir(parents=True, exist_ok=True)
        out_txt.write_text(txt_report, encoding="utf-8")
    if args.output_json:
        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json_report, encoding="utf-8")

    sys.stdout.write(txt_report)
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
