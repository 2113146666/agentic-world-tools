from __future__ import annotations

import argparse


def cmd_serve(args) -> None:
    import uvicorn

    uvicorn.run("agentic_world_tools.app:app", host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m agentic_world_tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve", help="工具台，默认 0.0.0.0:7777")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=7777)
    serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0
