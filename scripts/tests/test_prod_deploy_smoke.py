from __future__ import annotations

import unittest
from pathlib import Path

from scripts.prod_deploy_smoke import (
    REASON_DOCKER_ENGINE_DOWN,
    REASON_DOCKER_PERMISSION,
    REASON_PORT_CONFLICT,
    REASON_UNKNOWN,
    classify_compose_failure,
    classify_docker_failure,
    derive_json_path,
)


class ProdDeploySmokeTest(unittest.TestCase):
    def test_classify_docker_engine_down(self) -> None:
        text = "failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine"
        self.assertEqual(classify_docker_failure(text), REASON_DOCKER_ENGINE_DOWN)

    def test_classify_docker_permission(self) -> None:
        text = "permission denied while trying to connect to docker daemon socket"
        self.assertEqual(classify_docker_failure(text), REASON_DOCKER_PERMISSION)

    def test_classify_compose_port_conflict(self) -> None:
        text = "Bind for 0.0.0.0:8080 failed: port is already allocated"
        self.assertEqual(classify_compose_failure(text), REASON_PORT_CONFLICT)

    def test_classify_compose_unknown_maps_generic(self) -> None:
        self.assertNotEqual(classify_compose_failure("random failure"), REASON_UNKNOWN)

    def test_derive_json_path_from_txt(self) -> None:
        out_txt = Path("docs/review/mvp_verification_pack/artifacts/prod_deploy_smoke_20260302.txt")
        expected = Path("docs/review/mvp_verification_pack/artifacts/prod_deploy_smoke_20260302.json")
        self.assertEqual(derive_json_path(out_txt=out_txt, out_json=None), expected)


if __name__ == "__main__":
    unittest.main()
