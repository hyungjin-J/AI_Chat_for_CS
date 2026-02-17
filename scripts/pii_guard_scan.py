#!/usr/bin/env python3
"""Scan docs/code/log samples for potential PII or secret leakage."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_DIRS = [
    ROOT / 'docs',
    ROOT / 'src',
    ROOT / 'frontend' / 'src',
    ROOT / 'backend',
    ROOT / 'logs',
]

TEXT_EXT = {
    '.md', '.txt', '.csv', '.json', '.yml', '.yaml', '.xml', '.html', '.js', '.jsx', '.ts', '.tsx',
    '.py', '.java', '.kt', '.sql', '.properties', '.log', '.env', '.toml'
}

PATTERNS = [
    ('email', re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')),
    ('phone', re.compile(r'\b(?:\+?\d{1,3}[-. ]?)?(?:\(?\d{2,4}\)?[-. ]?)\d{3,4}[-. ]\d{4}\b')),
    ('order_like', re.compile(r'\b(?:order[_ -]?(?:id|no|number)|주문번호)\s*[:=]\s*["\']?[A-Za-z0-9_-]{6,}', re.IGNORECASE)),
    ('api_key_like', re.compile(r'\b(?:api[_-]?key|secret[_-]?key|private[_-]?key|FIGMA_API_KEY|FIGMA_OAUTH_TOKEN)\s*[:=]\s*["\']?[A-Za-z0-9._\-]{10,}', re.IGNORECASE)),
    ('access_token_like', re.compile(r'\b(?:access[_-]?token|refresh[_-]?token|authorization)\s*[:=]\s*["\']?(?:bearer\s+)?[A-Za-z0-9._\-]{12,}', re.IGNORECASE)),
]

IGNORE_SUBSTR = [
    '<access_token>', '<api_key>', '<secret_ref>', 'example.com', 'sample', 'dummy',
    'placeholder', 'YOUR_API_KEY', 'Bearer <access_token>'
]


class Finding:
    def __init__(self, path: Path, line_no: int, kind: str, snippet: str) -> None:
        self.path = path
        self.line_no = line_no
        self.kind = kind
        self.snippet = snippet


def iter_files() -> list[Path]:
    files: list[Path] = []
    for base in TARGET_DIRS:
        if not base.exists():
            continue
        for p in base.rglob('*'):
            if not p.is_file():
                continue
            if p.suffix.lower() not in TEXT_EXT:
                continue
            if any(part in {'.git', 'node_modules', 'build', 'dist', '.gradle'} for part in p.parts):
                continue
            files.append(p)
    return files


def should_ignore_line(line: str) -> bool:
    if '# pii-allow:' in line:
        return True
    lower = line.lower()
    return any(token.lower() in lower for token in IGNORE_SUBSTR)


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for enc in ('utf-8', 'utf-8-sig'):
        try:
            text = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            text = None
    if text is None:
        return findings

    for i, line in enumerate(text.splitlines(), start=1):
        if should_ignore_line(line):
            continue
        for kind, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, i, kind, line.strip()))
                break
    return findings


def main() -> int:
    findings: list[Finding] = []
    for p in iter_files():
        findings.extend(scan_file(p))

    if not findings:
        print('PII guard scan passed: no findings')
        return 0

    print(f'PII guard scan failed: {len(findings)} finding(s)')
    for item in findings:
        rel = item.path.relative_to(ROOT)
        print(f'- {rel}:{item.line_no} [{item.kind}] {item.snippet}')

    print('Tip: false positive는 해당 라인 끝에 "# pii-allow: reason"으로 예외 처리')
    return 1


if __name__ == '__main__':
    sys.exit(main())
