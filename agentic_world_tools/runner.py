from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from agentic_world_tools import jobs
from agentic_world_tools.paths import dist_target, frontend_root, repo_path, services

REPOS = ("agentic-world", "agentic-world-front", "agentic-world-tools")


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
    info = {"path": str(path), "exists": path.is_dir(), "branch": None, "head": None, "dirty": None}
    if not (path / ".git").exists():
        return info
    branch = subprocess.run(["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True)
    head = subprocess.run(["git", "-C", str(path), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(path), "status", "--porcelain"], capture_output=True, text=True)
    info["branch"] = (branch.stdout or "").strip() or None
    info["head"] = (head.stdout or "").strip() or None
    info["dirty"] = bool((dirty.stdout or "").strip())
    return info


def service_active(name: str) -> dict:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return {"id": name, "active": None, "detail": "无 systemctl（本机开发）"}
    proc = subprocess.run([systemctl, "is-active", name], capture_output=True, text=True)
    state = (proc.stdout or proc.stderr or "").strip() or "unknown"
    return {"id": name, "active": state == "active", "detail": state}


def stack_status() -> dict:
    repos = []
    for name in REPOS:
        item = git_head(repo_path(name))
        item["id"] = name
        repos.append(item)
    return {
        "port": 7777,
        "services": [service_active(name) for name in services()],
        "repos": repos,
        "job": jobs.current(),
    }


def _sudo_systemctl(job: dict, action: str, unit: str) -> int:
    argv = ["sudo", "-n", "systemctl", action, unit]
    code = run_cmd(job, argv, timeout=30)
    if code == 0:
        return 0
    jobs.append(job, "sudo -n 失败，改试不带 sudo")
    return run_cmd(job, ["systemctl", action, unit], timeout=30)


def update_stack(job: dict) -> None:
    ok = True
    try:
        for name in REPOS:
            path = repo_path(name)
            jobs.append(job, f"—— {name} @ {path}")
            if not path.is_dir():
                jobs.append(job, "目录不存在，跳过")
                ok = False
                continue
            if run_cmd(job, ["git", "-C", str(path), "pull", "--ff-only"], timeout=120) != 0:
                ok = False
                continue
            if name == "agentic-world":
                venv_pip = path / ".venv" / "bin" / "pip"
                venv_py = path / ".venv" / "bin" / "python"
                if venv_pip.exists():
                    run_cmd(job, [str(venv_pip), "install", "-r", "requirements.txt"], cwd=path, timeout=180)
                if venv_py.exists():
                    run_cmd(job, [str(venv_py), "-m", "unittest", "tests.test_agentic_world"], cwd=path, timeout=60)
                _sudo_systemctl(job, "restart", "agentic-world")
            elif name == "agentic-world-front":
                root = frontend_root(path)
                jobs.append(job, f"前端构建目录 {root}")
                env_cmd = ["env", "VITE_API_BASE_URL=", "npm", "install"]
                if run_cmd(job, env_cmd, cwd=root, timeout=180) != 0:
                    ok = False
                    continue
                if run_cmd(job, ["env", "VITE_API_BASE_URL=", "npm", "run", "build"], cwd=root, timeout=180) != 0:
                    ok = False
                    continue
                dist = root / "dist"
                target = dist_target()
                if not dist.is_dir():
                    jobs.append(job, "没有 dist/")
                    ok = False
                    continue
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
                _sudo_systemctl(job, "reload", "nginx")
            elif name == "agentic-world-tools":
                venv_pip = path / ".venv" / "bin" / "pip"
                if venv_pip.exists():
                    run_cmd(job, [str(venv_pip), "install", "-r", "requirements.txt"], cwd=path, timeout=180)
        if ok:
            jobs.append(job, "三仓更新结束，2 秒后重启 tools 自身")
            jobs.finish(job, True, status="restarting")
            subprocess.Popen(
                ["bash", "-c", "sleep 2; sudo -n systemctl restart agentic-world-tools || true"],
                start_new_session=True,
            )
        else:
            jobs.append(job, "有步骤失败，未重启 tools")
            jobs.finish(job, False)
    except Exception as exc:
        jobs.append(job, f"异常: {exc}")
        jobs.finish(job, False)
