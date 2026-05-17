"""启动脚本：依次启动 MCP Endpoint Server → MCP Pipe → app.py"""

import os
import signal
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_DIR = os.path.join(ROOT, "env")
SERVER_DIR = os.path.join(ROOT, "xiaozhi-esp32-server", "main", "xiaozhi-server")
MCP_ENDPOINT_DIR = os.path.join(ROOT, "mcp-endpoint-server")
MCP_PIPE_DIR = os.path.join(ROOT, "mcp-calculator")
PYTHON = os.path.join(ENV_DIR, "python.exe")

_background_processes = []


def _kill_all():
    for p in _background_processes:
        if p is not None and p.poll() is None:
            try:
                p.terminate()
            except Exception:
                pass
    for p in _background_processes:
        if p is not None and p.poll() is None:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    p.kill()
                except Exception:
                    pass


def _cleanup():
    if _background_processes:
        print("[main] 正在关闭后台服务...")
        _kill_all()
        print("[main] 后台服务已关闭")


def _wait_for_port(host, port, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def _start_mcp_endpoint(env):
    main_py = os.path.join(MCP_ENDPOINT_DIR, "main.py")
    if not os.path.exists(main_py):
        print(f"[main] 未找到 {main_py}，跳过 MCP Endpoint Server")
        return

    print(f"[main] 启动 MCP Endpoint Server ...")
    p = subprocess.Popen(
        [PYTHON, main_py],
        env=env,
        cwd=MCP_ENDPOINT_DIR,
        stdin=subprocess.DEVNULL,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    _background_processes.append(p)
    print(f"[main] MCP Endpoint Server 已启动 (pid={p.pid})")

    # 等待 8004 端口就绪
    print("[main] 等待 MCP Endpoint Server 就绪 ...")
    if _wait_for_port("127.0.0.1", 8004):
        print("[main] MCP Endpoint Server 就绪")
    else:
        print("[main] 警告：MCP Endpoint Server 启动超时，继续启动后续服务")


def _start_mcp_pipe(env):
    mcp_endpoint = env.get("MCP_ENDPOINT")
    if not mcp_endpoint:
        print("[main] 未设置 MCP_ENDPOINT，跳过 MCP pipe")
        return

    pipe_path = os.path.join(MCP_PIPE_DIR, "mcp_pipe.py")
    if not os.path.exists(pipe_path):
        print(f"[main] 未找到 {pipe_path}，跳过 MCP pipe")
        return

    print(f"[main] 启动 MCP pipe ...")
    p = subprocess.Popen(
        [PYTHON, pipe_path],
        env=env,
        cwd=MCP_PIPE_DIR,
        stdin=subprocess.DEVNULL,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    _background_processes.append(p)
    print(f"[main] MCP pipe 已启动 (pid={p.pid})")


def _load_dotenv(env):
    dotenv_path = os.path.join(SERVER_DIR, ".env")
    if not os.path.exists(dotenv_path):
        return
    from dotenv import load_dotenv
    load_dotenv(dotenv_path, override=False)
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())


def main():
    if not os.path.exists(PYTHON):
        print(f"错误：未找到 {PYTHON}")
        print("请先运行: conda create -p ./env --clone xiaozhi-esp32-server")
        sys.exit(1)

    env = os.environ.copy()
    env["PATH"] = os.pathsep.join([
        os.path.join(ENV_DIR, "Library", "bin"),
        os.path.join(ENV_DIR, "Library", "mingw-w64", "bin"),
        os.path.join(ENV_DIR, "Library", "usr", "bin"),
        os.path.join(ENV_DIR, "Scripts"),
        os.path.join(ENV_DIR, "bin"),
        os.path.join(ENV_DIR),
        env.get("PATH", ""),
    ])
    env["CONDA_PREFIX"] = ENV_DIR

    _load_dotenv(env)

    signal.signal(signal.SIGINT, lambda _sig, _frame: (_cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda _sig, _frame: (_cleanup(), sys.exit(0)))

    # 1. 启动 MCP Endpoint Server (:8004)
    _start_mcp_endpoint(env)

    # 2. 启动 MCP pipe（连接 :8004）
    _start_mcp_pipe(env)

    # 3. 启动 xiaozhi 服务端 (前台)
    print()
    print("$ conda activate ./env")
    print(f"$ cd xiaozhi-esp32-server/main/xiaozhi-server")
    print("$ python app.py")
    print()

    os.chdir(SERVER_DIR)
    try:
        result = subprocess.run([PYTHON, "app.py"], env=env)
        sys.exit(result.returncode)
    finally:
        _cleanup()


if __name__ == "__main__":
    main()
