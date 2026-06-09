"""
run_m4.py — M4 오케스트레이터: server_m4(모델/tf 프로세스) 기동 → 포트 대기 → client_m4(시뮬/EGL 프로세스) 실행 → 종료.

두 프로세스를 분리해 tf↔robosuite-EGL in-process 세그폴트를 회피. stdlib 만 사용(numpy/tf/torch import 안 함).
raw 출력은 verify/ 에 박제. PYTHONPATH/MUJOCO_GL 은 호출 환경에서 상속.
run: PYTHONPATH=$HOME/LIBERO MUJOCO_GL=egl python run_m4.py --num-tasks 2 --trials 5
"""

import argparse
import os
import pathlib
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify"
VERIFY.mkdir(exist_ok=True)
PY = sys.executable


def wait_port(host, port, timeout):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(1.0)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--num-tasks", type=int, default=2)
    ap.add_argument("--trials", type=int, default=5)
    args = ap.parse_args()

    server_log = (VERIFY / "m4-server.log").open("w")
    server = subprocess.Popen([PY, str(HERE / "server_m4.py")], stdout=server_log, stderr=subprocess.STDOUT, env=os.environ)
    try:
        print("[run_m4] waiting for server /act (model load ~3min)...", flush=True)
        if not wait_port("127.0.0.1", 8000, timeout=420):
            print("[run_m4] server did not open port 8000 in time", file=sys.stderr)
            return 1
        print("[run_m4] server up — launching client", flush=True)
        client = subprocess.run(
            [PY, str(HERE / "client_m4.py"), "--num-tasks", str(args.num_tasks), "--trials", str(args.trials)],
            capture_output=True, text=True, env=os.environ,
        )
        out = client.stdout + client.stderr
        (VERIFY / "m4-client.log").write_text(out)
        print(out, end="")
        print(f"[run_m4] client exit={client.returncode}")
        return client.returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
