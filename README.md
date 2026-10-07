# Agentic World Tools

运维工具台。一个 Python 进程，默认 `0.0.0.0:7777`，页面上可以看服务状态、按按钮跑工具。不是知识站，不并进控制面仓。

当前工具：一键更新&部署。拉取三个业务仓，只对 commit_id 变化的服务做构建和重启。

## 本机

```bash
cd agentic-world-tools
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest tests.test_tools
python -m agentic_world_tools serve --host 127.0.0.1 --port 7777
```

打开 http://127.0.0.1:7777/ 。本机没有 systemd 时，服务状态显示 n/a，更新仍会尝试 pull 工作区里并排的三个目录。

## 轻量机

仓库放到 `/opt/agentic-world-tools`。控制台防火墙放行 **TCP 7777**，来源 `0.0.0.0/0` 即可外网访问。不要把 8000 开到公网。这个端口上有部署按钮。

```bash
git clone git@github.com:2113146666/agentic-world-tools.git /opt/agentic-world-tools
cd /opt/agentic-world-tools
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest tests.test_tools

sudo cp deploy/agentic-world-tools.service /etc/systemd/system/
sudo cp deploy/sudoers /etc/sudoers.d/agentic-world-tools
sudo chmod 440 /etc/sudoers.d/agentic-world-tools
sudo visudo -cf /etc/sudoers.d/agentic-world-tools
sudo systemctl daemon-reload
sudo systemctl enable --now agentic-world-tools
curl -sS http://127.0.0.1:7777/health
```

浏览器：`http://公网IP:7777/`
