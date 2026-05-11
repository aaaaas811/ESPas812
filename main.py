"""XIAOZHI 项目便捷启动脚本

用法:
    python main.py start              仅启动 gateway + server
    python main.py build-flash-start  编译烧录 ESP32 并启动 gateway + server
    python main.py build              仅编译 ESP32 固件
    python main.py flash              仅烧录 ESP32

ESP-IDF 路径配置:
    - 优先使用环境变量 IDF_PATH
    - 否则按 IDF_DIRS 列表依次查找
    - 也可直接修改下方 IDF_DIRS
"""

import sys
import os
import subprocess
import time
import signal
from pathlib import Path

# ============================================================
# 配置
# ============================================================
ROOT = Path(__file__).resolve().parent
ESP32_DIR = ROOT / "xiaozhi-esp32"
SERVER_DIR = ROOT / "xiaozhi-esp32-server" / "main" / "xiaozhi-server"
GATEWAY_DIR = ROOT / "xiaozhi-mqtt-gateway"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
BOARD = "esp-sensairshuttle"

# ESP-IDF 查找路径（按顺序尝试）
IDF_DIRS = [
    os.environ.get("IDF_PATH", ""),
    "C:\\esp\\v5.5.2\\esp-idf",
    os.path.expandvars(r"%USERPROFILE%\esp\esp-idf"),
    os.path.expandvars(r"%USERPROFILE%\Desktop\esp-idf"),
]

processes = []


def find_idf_export():
    """查找 ESP-IDF 的 export.bat，返回完整路径。"""
    for d in IDF_DIRS:
        if not d:
            continue
        bat = Path(d) / "export.bat"
        if bat.exists():
            return str(bat)
    return None


def run_esp32(cmd, cwd=None):
    """在 ESP-IDF 环境中运行命令（Windows）。"""
    if cwd is None:
        cwd = ESP32_DIR

    export_bat = find_idf_export()
    if not export_bat:
        print("[FAIL] 找不到 ESP-IDF (export.bat)，请设置 IDF_PATH 环境变量")
        print("       已搜索的路径:")
        for d in IDF_DIRS:
            if d:
                print(f"         {d}")
        sys.exit(1)

    print(f"[INFO] ESP-IDF: {export_bat}")
    print(f"[CMD]  {cmd}")
    full_cmd = f'cmd /c "call \"{export_bat}\" && cd /d \"{cwd}\" && {cmd}"'
    result = subprocess.run(full_cmd, shell=True)
    if result.returncode != 0:
        print(f"[FAIL] 命令失败，退出码 {result.returncode}")
        sys.exit(1)


def run_normal(cmd, cwd):
    """在普通环境中运行命令。"""
    print(f"[CMD]  {cmd}  (cwd={cwd})")
    result = subprocess.run(cmd, shell=True, cwd=str(cwd))
    if result.returncode != 0:
        print(f"[FAIL] 命令失败，退出码 {result.returncode}")
        sys.exit(1)


def build_esp32():
    """编译 ESP32 固件（ESP-IDF 环境）。"""
    print("=" * 60)
    print("[BUILD] 编译 ESP32 固件 (board={}) ...".format(BOARD))
    run_esp32(f"python ./scripts/release.py {BOARD}")


def flash_esp32():
    """烧录 ESP32（ESP-IDF 环境）。"""
    print("=" * 60)
    print("[FLASH] 烧录 ESP32 ...")
    run_esp32("idf.py flash")


def start_gateway():
    """启动 MQTT 网关（后台进程）。"""
    print("[START] 启动 xiaozhi-mqtt-gateway ...")
    p = subprocess.Popen(
        "node app.js",
        shell=True,
        cwd=str(GATEWAY_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    processes.append(("gateway", p))
    time.sleep(1)


def start_server():
    """启动 AI 服务端（后台进程，使用 .venv）。"""
    print("[START] 启动 xiaozhi-esp32-server ...")
    p = subprocess.Popen(
        str(VENV_PYTHON) + " app.py",
        shell=True,
        cwd=str(SERVER_DIR),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    processes.append(("server", p))
    time.sleep(1)


def stop_all():
    """关闭所有后台进程。"""
    print("\n[STOP] 正在关闭所有服务 ...")
    for name, p in processes:
        if p.poll() is None:
            print(f"  关闭 {name} (pid={p.pid}) ...")
            p.terminate()
    for name, p in processes:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    print("[STOP] 所有服务已关闭")


def cmd_start():
    """启动 gateway + server 并等待退出。"""
    print("=" * 60)
    print("启动 XIAOZHI 服务 ...")
    start_gateway()
    start_server()
    print("=" * 60)
    print("所有服务已启动。按 Ctrl+C 停止。")

    def on_signal(sig, frame):
        stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    while True:
        for name, p in list(processes):
            if p.poll() is not None:
                print(f"[WARN] {name} 意外退出，退出码 {p.returncode}")
                stop_all()
                sys.exit(1)
        time.sleep(2)


def cmd_build_flash_start():
    """编译 + 烧录 + 启动。"""
    build_esp32()
    flash_esp32()
    print("=" * 60)
    print("ESP32 烧录完成，启动服务 ...")
    cmd_start()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        cmd_start()
    elif cmd == "build":
        build_esp32()
    elif cmd == "flash":
        flash_esp32()
    elif cmd in ("build-flash-start", "bfs"):
        cmd_build_flash_start()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
