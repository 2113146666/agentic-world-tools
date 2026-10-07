from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agentic_world_tools import jobs
from agentic_world_tools.paths import (
    REPOS,
    dist_target,
    frontend_root,
    log_path,
    repo_path,
    services,
)


def commit_changed(before: str | None, after: str | None) -> bool:
    return bool(after) and after != before


def run_cmd(job: dict, argv: list[str], cwd: Path | None = None, timeout: int = 180) -> int:
    jobs.append(job, "$ " + " ".join(argv) + (f"  (in {cwd})" if cwd else ""))
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        jobs.append(job, f"超时（{timeout}s）")
        return 124
    except FileNotFoundError as exc:
        jobs.append(job, f"找不到命令: {exc}")
        return 127
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if out:
        jobs.append(job, out)
    if err:
        jobs.append(job, err)
    jobs.append(job, f"exit {proc.returncode}")
    return proc.returncode


def git_head(path: Path) -> dict:
    info = {
        "path": str(path),
        "exists": path.is_dir(),
        "branch": None,
        "commit_id": None,
        "dirty": None,
    }
    if not (path / ".git").exists():
        return info
    branch = subprocess.run(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    commit = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(path), "status", "--porcelain"], capture_output=True, text=True)
    info["branch"] = (branch.stdout or "").strip() or None
    info["commit_id"] = (commit.stdout or "").strip() or None
    info["dirty"] = bool((dirty.stdout or "").strip())
    return info


def service_active(name: str) -> dict:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return {"id": name, "active": False, "status": "未启动"}
    proc = subprocess.run([systemctl, "is-active", name], capture_output=True, text=True)
    active = (proc.stdout or "").strip() == "active"
    return {"id": name, "active": active, "status": "运行中" if active else "未启动"}


def stack_status() -> dict:
    repos = []
    for name in REPOS:
        item = git_head(repo_path(name))
        item["id"] = name
        repos.append(item)
    logs = [{"id": name, "log_path": log_path(name)} for name in services()]
    return {
        "port": 7777,
        "services": [service_active(name) for name in services()],
        "repos": repos,
        "logs": logs,
        "job": jobs.current(),
    }


def _sudo_systemctl(job: dict, action: str, unit: str) -> int:
    argv = ["sudo", "-n", "systemctl", action, unit]
    code = run_cmd(job, argv, timeout=30)
    if code == 0:
        return 0
    jobs.append(job, "sudo -n 失败，改试不带 sudo")
    return run_cmd(job, ["systemctl", action, unit], timeout=30)


def _deploy_api(job: dict, path: Path) -> bool:
    venv_pip = path / ".venv" / "bin" / "pip"
    venv_py = path / ".venv" / "bin" / "python"
    if venv_pip.exists():
        if run_cmd(job, [str(venv_pip), "install", "-r", "requirements.txt"], cwd=path, timeout=180) != 0:
            return False
    if venv_py.exists():
        if run_cmd(job, [str(venv_py), "-m", "unittest", "tests.test_agentic_world"], cwd=path, timeout=60) != 0:
            return False
    return _sudo_systemctl(job, "restart", "agentic-world") == 0


def _deploy_front(job: dict, path: Path) -> bool:
    root = frontend_root(path)
    jobs.append(job, f"前端构建目录 {root}")
    if run_cmd(job, ["env", "VITE_API_BASE_URL=", "npm", "install"], cwd=root, timeout=180) != 0:
        return False
    if run_cmd(job, ["env", "VITE_API_BASE_URL=", "npm", "run", "build"], cwd=root, timeout=180) != 0:
        return False
    dist = root / "dist"
    target = dist_target()
    if not dist.is_dir():
        jobs.append(job, "没有 dist/")
        return False
    target.mkdir(parents=True, exist_ok=True)
    for item in dist.iterdir():
        dest = target / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    jobs.append(job, f"已拷 dist → {target}")
    return True


def _deploy_tools(job: dict, path: Path) -> bool:
    venv_pip = path / ".venv" / "bin" / "pip"
    if venv_pip.exists():
        if run_cmd(job, [str(venv_pip), "install", "-r", "requirements.txt"], cwd=path, timeout=180) != 0:
            return False
    unit = path / "deploy" / "agentic-world-tools.service"
    if unit.exists():
        run_cmd(job, ["sudo", "-n", "cp", str(unit), "/etc/systemd/system/agentic-world-tools.service"], timeout=15)
        run_cmd(job, ["sudo", "-n", "systemctl", "daemon-reload"], timeout=15)
    return True


def update_stack(job: dict) -> None:
    ok = True
    tools_changed = False
    try:
        for name in REPOS:
            path = repo_path(name)
            jobs.append(job, f"—— {name} @ {path}")
            if not path.is_dir():
                jobs.append(job, "目录不存在，跳过")
                ok = False
                continue
            before = git_head(path).get("commit_id")
            if run_cmd(job, ["git", "-C", str(path), "pull", "--ff-only"], timeout=120) != 0:
                ok = False
                continue
            after = git_head(path).get("commit_id")
            if not commit_changed(before, after):
                jobs.append(job, f"commit 未变 {after or '-'}，不重启")
                continue
            jobs.append(job, f"commit {before} → {after}，部署")
            if name == "agentic-world":
                if not _deploy_api(job, path):
                    ok = False
            elif name == "agentic-world-front":
                if not _deploy_front(job, path):
                    ok = False
            elif name == "agentic-world-tools":
                tools_changed = True
                if not _deploy_tools(job, path):
                    ok = False
        if not ok:
            jobs.append(job, "有步骤失败，未重启 tools")
            jobs.finish(job, False)
            return
        if tools_changed:
            jobs.append(job, "tools commit 已变，2 秒后重启自身")
            jobs.finish(job, True, status="restarting")
            subprocess.Popen(
                ["bash", "-c", "sleep 2; sudo -n systemctl restart agentic-world-tools || true"],
                start_new_session=True,
            )
            return
        jobs.append(job, "全部完成，无需重启 tools")
        jobs.finish(job, True)
    except Exception as exc:
        jobs.append(job, f"异常: {exc}")
        jobs.finish(job, False)
