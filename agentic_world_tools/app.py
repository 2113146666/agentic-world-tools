from __future__ import annotations

import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agentic_world_tools import __version__, jobs
from agentic_world_tools.paths import STATIC_DIR
from agentic_world_tools.runner import stack_status, update_stack

app = FastAPI(title="Agentic World Tools", version=__version__)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

TOOLS = [
    {
        "id": "update-stack",
        "name": "一键更新&部署",
        "description": "一键拉取所有业务服务的最新代码，并重启commit_id发生变化的服务",
        "path": "/api/tools/update-stack",
        "dangerous": True,
    }
]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agentic-world-tools"}


@app.get("/api/health")
def api_health() -> dict:
    return health()


@app.get("/api/status")
def api_status() -> dict:
    return stack_status()


@app.get("/api/tools")
def api_tools() -> dict:
    return {"tools": TOOLS}


@app.get("/api/jobs/latest")
def api_job_latest():
    job = jobs.current()
    if not job:
        return JSONResponse({"job": None})
    return {"job": job}


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    job = jobs.load(job_id)
    if not job:
        raise HTTPException(404, "没有这个任务")
    return {"job": job}


@app.post("/api/tools/update-stack")
def api_update_stack() -> dict:
    try:
        job = jobs.new_job("update-stack")
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    threading.Thread(target=update_stack, args=(job,), daemon=True).start()
    return {"job": job}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
