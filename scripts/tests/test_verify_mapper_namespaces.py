from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "verify_mapper_namespaces.py"


def write_contract(path: Path) -> None:
    contract = {
        "java_root": "backend/src/main/java",
        "xml_root": "backend/src/main/resources/mappers",
        "mapper_interface_glob": "**/domain/**/mapper/*Mapper.java",
        "allowed_xml_contexts": ["conversation", "identity", "knowledge", "operations", "billing", "platform"],
        "namespace_context_map": {
            "com.aichatbot.contexts.conversation.": "conversation",
            "com.aichatbot.contexts.identity.": "identity",
            "com.aichatbot.contexts.knowledge.": "knowledge",
            "com.aichatbot.contexts.operations.": "operations",
            "com.aichatbot.contexts.billing.": "billing",
            "com.aichatbot.platform.": "platform",
        },
        "legacy_namespace_prefixes": ["com.aichatbot.auth.", "com.aichatbot.billing."],
    }
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class VerifyMapperNamespaceTest(unittest.TestCase):
    def test_pass_when_namespace_and_path_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            java_file = root / "backend/src/main/java/com/aichatbot/platform/tenancy/domain/mapper/TenantResolverMapper.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.aichatbot.platform.tenancy.domain.mapper;\n\n"
                "public interface TenantResolverMapper {}\n",
                encoding="utf-8",
            )

            xml_file = root / "backend/src/main/resources/mappers/platform/TenantResolverMapper.xml"
            xml_file.parent.mkdir(parents=True, exist_ok=True)
            xml_file.write_text(
                "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
                "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" "
                "\"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">\n"
                "<mapper namespace=\"com.aichatbot.platform.tenancy.domain.mapper.TenantResolverMapper\">\n"
                "  <select id=\"findTenantIdByKey\" resultType=\"java.lang.String\">SELECT 1</select>\n"
                "</mapper>\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
            self.assertIn("status=PASS", proc.stdout)

    def test_fail_when_duplicate_namespace_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            java_file = root / "backend/src/main/java/com/aichatbot/contexts/identity/domain/mapper/AuthMapper.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.aichatbot.contexts.identity.domain.mapper;\n\n"
                "public interface AuthMapper {}\n",
                encoding="utf-8",
            )

            namespace = "com.aichatbot.contexts.identity.domain.mapper.AuthMapper"
            for idx in (1, 2):
                xml_file = root / f"backend/src/main/resources/mappers/identity/AuthMapper_{idx}.xml"
                xml_file.parent.mkdir(parents=True, exist_ok=True)
                xml_file.write_text(
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
                    "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" "
                    "\"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">\n"
                    f"<mapper namespace=\"{namespace}\">\n"
                    "  <select id=\"find\" resultType=\"java.lang.String\">SELECT 1</select>\n"
                    "</mapper>\n",
                    encoding="utf-8",
                )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("NAMESPACE_DUPLICATED", proc.stdout)

    def test_fail_on_legacy_namespace_and_context_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = root / "contract.json"
            write_contract(contract_path)

            java_file = root / "backend/src/main/java/com/aichatbot/platform/tenancy/domain/mapper/TenantResolverMapper.java"
            java_file.parent.mkdir(parents=True, exist_ok=True)
            java_file.write_text(
                "package com.aichatbot.platform.tenancy.domain.mapper;\n\n"
                "public interface TenantResolverMapper {}\n",
                encoding="utf-8",
            )

            xml_file = root / "backend/src/main/resources/mappers/identity/TenantResolverMapper.xml"
            xml_file.parent.mkdir(parents=True, exist_ok=True)
            xml_file.write_text(
                "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n"
                "<!DOCTYPE mapper PUBLIC \"-//mybatis.org//DTD Mapper 3.0//EN\" "
                "\"http://mybatis.org/dtd/mybatis-3-mapper.dtd\">\n"
                "<mapper namespace=\"com.aichatbot.auth.domain.mapper.AuthMapper\">\n"
                "  <select id=\"find\" resultType=\"java.lang.String\">SELECT 1</select>\n"
                "</mapper>\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [
                    "python",
                    str(SCRIPT_PATH),
                    "--root",
                    str(root),
                    "--contract",
                    str(contract_path),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("LEGACY_NAMESPACE_FORBIDDEN", proc.stdout)
            self.assertIn("NAMESPACE_CONTEXT_UNKNOWN", proc.stdout)


if __name__ == "__main__":
    unittest.main()
