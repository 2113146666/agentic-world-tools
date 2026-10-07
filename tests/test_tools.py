from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentic_world_tools.paths import TOOLS_ROOT, frontend_root, repo_path
from agentic_world_tools import jobs


class PathTests(unittest.TestCase):
    def test_tools_repo_is_this_tree(self) -> None:
        self.assertTrue((TOOLS_ROOT / "requirements.txt").exists())
        self.assertEqual(repo_path("agentic-world-tools"), TOOLS_ROOT)

    def test_frontend_nested_or_flat(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            nested = root / "agentic-world-front"
            nested.mkdir()
            (nested / "package.json").write_text("{}", encoding="utf-8")
            self.assertEqual(frontend_root(root), nested)
            flat = root / "flat"
            flat.mkdir()
            (flat / "package.json").write_text("{}", encoding="utf-8")
            self.assertEqual(frontend_root(flat), flat)


class JobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patcher = patch("agentic_world_tools.jobs.DATA_DIR", Path(self.tmp.name))
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        jobs._current = None

    def test_single_runner(self) -> None:
        first = jobs.new_job("update-stack")
        with self.assertRaises(RuntimeError):
            jobs.new_job("update-stack")
        jobs.finish(first, True)
        second = jobs.new_job("update-stack")
        self.assertNotEqual(first["id"], second["id"])


if __name__ == "__main__":
    unittest.main()
