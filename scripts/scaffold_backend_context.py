#!/usr/bin/env python3
"""Scaffold a backend bounded context using the DDD template."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class GeneratedFile:
    path: Path
    content: str


def normalize_name(raw: str, label: str) -> str:
    value = raw.strip().lower()
    if not NAME_PATTERN.fullmatch(value):
        raise ValueError(
            f"{label} must match {NAME_PATTERN.pattern}; got {raw!r}"
        )
    return value


def to_pascal_case(value: str) -> str:
    parts = [part for part in re.split(r"[_\-]+", value) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def build_files(
    context: str,
    java_root: Path,
    mapper_root: Path,
    test_root: Path,
) -> list[GeneratedFile]:
    context_class = to_pascal_case(context)
    package_root = f"com.aichatbot.contexts.{context}"
    context_root = java_root / context
    test_context_root = test_root / context
    mapper_context_root = mapper_root / context

    files: list[GeneratedFile] = [
        GeneratedFile(
            path=context_root / "domain/model" / f"{context_class}AggregateRoot.java",
            content=(
                f"package {package_root}.domain.model;\n\n"
                f"public final class {context_class}AggregateRoot {{\n"
                "    private final String id;\n\n"
                f"    public {context_class}AggregateRoot(String id) {{\n"
                "        this.id = id;\n"
                "    }\n\n"
                "    public String id() {\n"
                "        return id;\n"
                "    }\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "domain/service" / f"{context_class}DomainService.java",
            content=(
                f"package {package_root}.domain.service;\n\n"
                f"public interface {context_class}DomainService {{\n"
                "    void validatePolicy();\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "domain/mapper" / f"{context_class}Mapper.java",
            content=(
                f"package {package_root}.domain.mapper;\n\n"
                f"public interface {context_class}Mapper {{\n"
                "    int ping();\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "application/usecase" / f"{context_class}UseCase.java",
            content=(
                f"package {package_root}.application.usecase;\n\n"
                f"import {package_root}.application.dto.{context_class}Command;\n\n"
                f"public interface {context_class}UseCase {{\n"
                f"    void execute({context_class}Command command);\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "application/dto" / f"{context_class}Command.java",
            content=(
                f"package {package_root}.application.dto;\n\n"
                f"public record {context_class}Command(String traceId, String tenantKey) {{\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root
            / "infrastructure/persistence/mybatis"
            / f"{context_class}MybatisRepository.java",
            content=(
                f"package {package_root}.infrastructure.persistence.mybatis;\n\n"
                f"import {package_root}.domain.mapper.{context_class}Mapper;\n\n"
                f"public final class {context_class}MybatisRepository {{\n"
                f"    private final {context_class}Mapper mapper;\n\n"
                f"    public {context_class}MybatisRepository({context_class}Mapper mapper) {{\n"
                "        this.mapper = mapper;\n"
                "    }\n\n"
                "    public int ping() {\n"
                "        return mapper.ping();\n"
                "    }\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "infrastructure/external" / f"{context_class}ExternalGateway.java",
            content=(
                f"package {package_root}.infrastructure.external;\n\n"
                f"public interface {context_class}ExternalGateway {{\n"
                "    void call();\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "presentation/controller" / f"{context_class}Controller.java",
            content=(
                f"package {package_root}.presentation.controller;\n\n"
                f"public final class {context_class}Controller {{\n"
                "    // Keep controller thin: map request/response and delegate to use case.\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "presentation/request" / f"{context_class}Request.java",
            content=(
                f"package {package_root}.presentation.request;\n\n"
                f"public record {context_class}Request(String traceId, String tenantKey) {{\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "presentation/response" / f"{context_class}Response.java",
            content=(
                f"package {package_root}.presentation.response;\n\n"
                f"public record {context_class}Response(String status) {{\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=mapper_context_root / f"{context_class}Mapper.xml",
            content=(
                '<?xml version="1.0" encoding="UTF-8" ?>\n'
                '<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" '
                '"http://mybatis.org/dtd/mybatis-3-mapper.dtd">\n'
                f'<mapper namespace="{package_root}.domain.mapper.{context_class}Mapper">\n'
                '    <select id="ping" resultType="int">\n'
                "        SELECT 1\n"
                "    </select>\n"
                "</mapper>\n"
            ),
        ),
        GeneratedFile(
            path=test_context_root / f"{context_class}ArchitectureSmokeTest.java",
            content=(
                f"package com.aichatbot.contexts.{context};\n\n"
                "import org.junit.jupiter.api.Test;\n\n"
                "import static org.junit.jupiter.api.Assertions.assertTrue;\n\n"
                f"class {context_class}ArchitectureSmokeTest {{\n"
                "    @Test\n"
                "    void templateLoads() {\n"
                "        assertTrue(true);\n"
                "    }\n"
                "}\n"
            ),
        ),
        GeneratedFile(
            path=context_root / "README.md",
            content=(
                f"# {context_class} Context\n\n"
                "Generated by `scripts/scaffold_backend_context.py`.\n\n"
                "Rules:\n"
                "- Keep domain policy inside this context.\n"
                "- Keep controller thin.\n"
                "- Keep mapper namespace aligned with mapper interface FQCN.\n"
            ),
        ),
    ]
    return files


def report(status: str, context: str, dry_run: bool, created: list[Path], existing: list[Path]) -> dict:
    payload = {
        "status": status,
        "context": context,
        "dry_run": dry_run,
        "created_count": len(created),
        "created_paths": [p.as_posix() for p in created],
        "existing_count": len(existing),
        "existing_paths": [p.as_posix() for p in existing],
    }
    return payload


def write_output(payload: dict, output_json: str | None) -> None:
    lines = [
        "backend_context_scaffold",
        f"status={payload['status']}",
        f"context={payload['context']}",
        f"dry_run={1 if payload['dry_run'] else 0}",
        f"created_count={payload['created_count']}",
        f"existing_count={payload['existing_count']}",
    ]
    for path in payload["existing_paths"]:
        lines.append(f"- existing={path}")
    for path in payload["created_paths"]:
        lines.append(f"- created={path}")

    if payload["status"] == "FAIL":
        lines.append("remediation=Use --force to overwrite, or remove conflicting files first.")
    else:
        lines.append("next_action=Wire generated files into real use cases before production use.")

    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if output_json:
        out = Path(output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold backend context directories and starter files")
    parser.add_argument("--context", required=True, help="Context name (snake_case)")
    parser.add_argument(
        "--java-root",
        default="backend/src/main/java/com/aichatbot/contexts",
        help="Root path for backend context java packages",
    )
    parser.add_argument(
        "--mapper-root",
        default="backend/src/main/resources/mappers",
        help="Root path for MyBatis mapper XML files",
    )
    parser.add_argument(
        "--test-root",
        default="backend/src/test/java/com/aichatbot/contexts",
        help="Root path for context tests",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print files that would be created")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--output-json", help="Optional JSON report path")
    args = parser.parse_args()

    try:
        context = normalize_name(args.context, "context")
    except ValueError as exc:
        payload = {
            "status": "FAIL",
            "context": args.context,
            "dry_run": args.dry_run,
            "created_count": 0,
            "created_paths": [],
            "existing_count": 0,
            "existing_paths": [],
            "error": str(exc),
        }
        write_output(payload=payload, output_json=args.output_json)
        return 1

    java_root = Path(args.java_root)
    mapper_root = Path(args.mapper_root)
    test_root = Path(args.test_root)

    targets = build_files(
        context=context,
        java_root=java_root,
        mapper_root=mapper_root,
        test_root=test_root,
    )

    existing = [item.path for item in targets if item.path.exists()]
    if existing and not args.force:
        payload = report(
            status="FAIL",
            context=context,
            dry_run=args.dry_run,
            created=[],
            existing=existing,
        )
        write_output(payload=payload, output_json=args.output_json)
        return 1

    created: list[Path] = []
    if not args.dry_run:
        for item in targets:
            item.path.parent.mkdir(parents=True, exist_ok=True)
            item.path.write_text(item.content, encoding="utf-8", errors="strict")
            created.append(item.path)
    else:
        created = [item.path for item in targets]

    payload = report(
        status="PASS",
        context=context,
        dry_run=args.dry_run,
        created=created,
        existing=existing,
    )
    write_output(payload=payload, output_json=args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
