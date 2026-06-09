"""
run.py — 오케스트레이터: server(모델/tf 프로세스) 기동 → 포트 대기 → client(시뮬/EGL 프로세스) 실행 → 종료.

두 프로세스를 분리해 tf↔robosuite-EGL in-process 세그폴트를 회피. stdlib 만 사용(numpy/tf/torch import 안 함).
raw 출력은 verify/ 에 박제. PYTHONPATH/MUJOCO_GL 은 호출 환경에서 상속.
run: PYTHONPATH=$HOME/LIBERO MUJOCO_GL=egl python run.py --suite libero_spatial --tasks 2 --trials 5
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
    ap = argparse.ArgumentParser(description="로컬 VLA eval: 모델(서버)↔시뮬(클라) 프로세스 분리 오케스트레이터")
    ap.add_argument("--policy", default="openvla", choices=["openvla"],
                    help="정책 어댑터 (현재 openvla; 2번째 정책은 server.py 에 어댑터 추가)")
    ap.add_argument("--suite", default="libero_spatial",
                    help="LIBERO 태스크 스위트 (libero_spatial/object/goal/10 ...)")
    ap.add_argument("--ckpt", default="",
                    help="HF 체크포인트 (비우면 openvla/openvla-7b-finetuned-<suite>)")
    ap.add_argument("--tasks", type=int, default=2, help="스위트 내 태스크 수")
    ap.add_argument("--trials", type=int, default=5, help="태스크당 rollout 수")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    server_cmd = [PY, str(HERE / "server.py"), "--policy", args.policy, "--suite", args.suite, "--port", str(args.port)]
    if args.ckpt:
        server_cmd += ["--ckpt", args.ckpt]

    server_log = (VERIFY / "server.log").open("w")
    server = subprocess.Popen(server_cmd, stdout=server_log, stderr=subprocess.STDOUT, env=os.environ)
    try:
        print(f"[run] waiting for server /act on :{args.port} (model load ~3min)...", flush=True)
        if not wait_port("127.0.0.1", args.port, timeout=420):
            print(f"[run] server did not open port {args.port} in time", file=sys.stderr)
            return 1
        print("[run] server up — launching client", flush=True)
        client = subprocess.run(
            [PY, str(HERE / "client.py"), "--suite", args.suite,
             "--tasks", str(args.tasks), "--trials", str(args.trials), "--port", str(args.port)],
            capture_output=True, text=True, env=os.environ,
        )
        out = client.stdout + client.stderr
        (VERIFY / "client.log").write_text(out)
        print(out, end="")
        print(f"[run] client exit={client.returncode}")
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
