from __future__ import annotations

import os
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = TOOLS_ROOT / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# 仓库在 /opt 下并排，或在本机工作区并排。
OPT = Path(os.environ.get("AW_OPT", str(TOOLS_ROOT.parent)))


def repo_path(name: str) -> Path:
    if name == "agentic-world-tools":
        return TOOLS_ROOT
    return OPT / name


def frontend_root(front: Path) -> Path:
    if (front / "package.json").exists():
        return front
    nested = front / "agentic-world-front"
    if (nested / "package.json").exists():
        return nested
    matches = sorted(front.glob("*/package.json"))
    if matches:
        return matches[0].parent
    return front


def dist_target() -> Path:
    return Path(os.environ.get("AW_FRONT_DIST", "/var/www/agentic-world-front"))


def services() -> list[str]:
    return ["agentic-world", "nginx", "agentic-world-tools"]
