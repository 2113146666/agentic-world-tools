from __future__ import annotations

import os
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = TOOLS_ROOT / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# 仓库在 /opt 下并排，或在本机工作区并排。
OPT = Path(os.environ.get("AW_OPT", str(TOOLS_ROOT.parent)))

SERVICE_UNITS = ("agentic-world", "nginx", "agentic-world-tools")
REPOS = ("agentic-world", "agentic-world-front", "agentic-world-tools")

LOG_PATHS = {
    "agentic-world": str(OPT / "agentic-world" / "data" / "service.log"),
    "nginx": "/var/log/nginx/error.log",
    "agentic-world-tools": str(TOOLS_ROOT / "data" / "service.log"),
}


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
    return list(SERVICE_UNITS)


def log_path(name: str) -> str:
    return LOG_PATHS.get(name, "")
