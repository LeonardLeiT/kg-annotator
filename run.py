from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from threading import Timer


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start KG Annotator backend and frontend.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host for both services")
    parser.add_argument("--backend-port", type=int, default=8000)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--no-reload", action="store_true", help="Disable backend auto-reload")
    parser.add_argument("--open", action="store_true", help="Open the frontend in a browser")
    return parser.parse_args()


def _npm_command() -> str:
    executable = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not executable:
        raise RuntimeError("未找到 npm，请先安装 Node.js 并执行 frontend 目录下的 npm install")
    return executable


def _frontend_command(args: argparse.Namespace) -> list[str]:
    local_vite = FRONTEND_DIR / "node_modules" / ".bin" / (
        "vite.cmd" if os.name == "nt" else "vite"
    )
    if local_vite.is_file():
        return [
            str(local_vite),
            "--host",
            args.host,
            "--port",
            str(args.frontend_port),
            "--configLoader",
            "runner",
        ]
    return [
        _npm_command(),
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.frontend_port),
    ]


def build_commands(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    backend = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.backend_port),
    ]
    if not args.no_reload:
        backend.append("--reload")
    frontend = _frontend_command(args)
    return backend, frontend


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def main() -> int:
    args = parse_args()
    if not (BACKEND_DIR / "app" / "main.py").is_file():
        raise RuntimeError(f"后端入口不存在: {BACKEND_DIR / 'app' / 'main.py'}")
    if not (FRONTEND_DIR / "package.json").is_file():
        raise RuntimeError(f"前端入口不存在: {FRONTEND_DIR / 'package.json'}")

    backend_command, frontend_command = build_commands(args)
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    environment["VITE_API_URL"] = f"http://{args.host}:{args.backend_port}/api"
    frontend_origin = f"http://{args.host}:{args.frontend_port}"
    configured_origins = [
        item.strip()
        for item in environment.get("CORS_ORIGINS", "").split(",")
        if item.strip()
    ]
    if frontend_origin not in configured_origins:
        configured_origins.append(frontend_origin)
    environment["CORS_ORIGINS"] = ",".join(configured_origins)
    processes: list[subprocess.Popen[bytes]] = []
    try:
        print(f"Backend: http://{args.host}:{args.backend_port}")
        print(f"Frontend: http://{args.host}:{args.frontend_port}")
        processes.append(subprocess.Popen(backend_command, cwd=BACKEND_DIR, env=environment))
        processes.append(subprocess.Popen(frontend_command, cwd=FRONTEND_DIR, env=environment))
        if args.open:
            Timer(1.5, webbrowser.open, args=(f"http://{args.host}:{args.frontend_port}",)).start()

        while True:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    return return_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes):
            _stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
