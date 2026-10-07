from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from agentic_world_tools.paths import DATA_DIR

_lock = threading.Lock()
_current: dict | None = None


def _job_path(job_id: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"job-{job_id}.json"


def latest_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "latest.json"


def new_job(tool_id: str) -> dict:
    global _current
    with _lock:
        if _current and _current.get("status") in ("running", "restarting"):
            raise RuntimeError("已有工具在跑，等它结束")
        job = {
            "id": uuid.uuid4().hex[:12],
            "tool_id": tool_id,
            "status": "running",
            "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "finished": None,
            "ok": None,
            "lines": [],
        }
        _current = job
        _persist(job)
        return job


def append(job: dict, line: str) -> None:
    with _lock:
        job["lines"].append(line)
        _persist(job)


def finish(job: dict, ok: bool, status: str = "done") -> None:
    global _current
    with _lock:
        job["ok"] = ok
        job["status"] = status
        job["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _current = job
        _persist(job)


def current() -> dict | None:
    global _current
    with _lock:
        job = _current
        if job is None:
            path = latest_path()
            if path.exists():
                job = json.loads(path.read_text(encoding="utf-8"))
                _current = job
        if job and job.get("status") == "restarting":
            # 能响应请求说明进程已起来，重启完成。不把 restarting 留在磁盘上，否则按钮会永远禁用。
            job["status"] = "done"
            job["ok"] = True
            job["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            job.setdefault("lines", []).append("tools 已重新拉起")
            _persist(job)
        if not job:
            return None
        return json.loads(json.dumps(job))


def load(job_id: str) -> dict | None:
    path = _job_path(job_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    job = current()
    if job and job.get("id") == job_id:
        return job
    return None


def _persist(job: dict) -> None:
    text = json.dumps(job, ensure_ascii=False, indent=2)
    _job_path(job["id"]).write_text(text, encoding="utf-8")
    latest_path().write_text(text, encoding="utf-8")
