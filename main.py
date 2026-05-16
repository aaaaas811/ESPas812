"""启动脚本：使用项目本地 conda 环境运行 app.py + MCP pipe"""

import os
import signal
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_DIR = os.path.join(ROOT, "env")
SERVER_DIR = os.path.join(ROOT, "xiaozhi-esp32-server", "main", "xiaozhi-server")
MCP_PIPE_DIR = os.path.join(ROOT, "mcp-calculator")
PYTHON = os.path.join(ENV_DIR, "python.exe")

_mcp_process = None


def _cleanup():
    global _mcp_process
    if _mcp_process is not None and _mcp_process.poll() is None:
        print("[main] 正在关闭 MCP pipe...")
        _mcp_process.terminate()
        try:
            _mcp_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _mcp_process.kill()
        print("[main] MCP pipe 已关闭")


def _start_mcp_pipe(env):
    global _mcp_process
    mcp_endpoint = env.get("MCP_ENDPOINT")
    if not mcp_endpoint:
        print("[main] 未设置 MCP_ENDPOINT，跳过 MCP pipe 启动")
        return

    mcp_pipe_path = os.path.join(MCP_PIPE_DIR, "mcp_pipe.py")
    if not os.path.exists(mcp_pipe_path):
        print(f"[main] 未找到 {mcp_pipe_path}，跳过 MCP pipe 启动")
        return

    print(f"[main] 启动 MCP pipe: {mcp_pipe_path}")
    _mcp_process = subprocess.Popen(
        [PYTHON, mcp_pipe_path],
        env=env,
        cwd=MCP_PIPE_DIR,
        stdin=subprocess.DEVNULL,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    print(f"[main] MCP pipe 已启动 (pid={_mcp_process.pid})")


def main():
    if not os.path.exists(PYTHON):
        print(f"错误：未找到 {PYTHON}")
        print("请先运行: conda create -p ./env --clone xiaozhi-esp32-server")
        sys.exit(1)

    env = os.environ.copy()
    # 将 conda 环境的 bin 目录加入 PATH，确保 DLL（如 opus.dll）可被找到
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

    # 从 .env 文件加载环境变量（mcp_pipe.py 内部也用了 dotenv，这里双重保险）
    dotenv_path = os.path.join(ROOT, "xiaozhi-esp32-server", "main", "xiaozhi-server", ".env")
    if os.path.exists(dotenv_path):
        from dotenv import load_dotenv
        load_dotenv(dotenv_path, override=False)
        # 将 .env 变量合并到 env
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env.setdefault(k.strip(), v.strip())

    # 启动 MCP pipe（后台进程）
    _start_mcp_pipe(env)

    signal.signal(signal.SIGINT, lambda _sig, _frame: (_cleanup(), sys.exit(0)))
    signal.signal(signal.SIGTERM, lambda _sig, _frame: (_cleanup(), sys.exit(0)))

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
