"""
run_m1.py — M1 mock round-trip 오케스트레이터 (bash 멀티라인/CRLF 마찰 회피).

mock_server 를 subprocess 로 띄우고 → 포트 대기 → mock_client 실행 → 종료.
raw 출력은 verify/ 에 박제. exit 0 = M1 PASS.

run: ~/.venvs/vla-eval/bin/python run_m1.py
"""

import pathlib
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
VERIFY = HERE / "verify"
VERIFY.mkdir(exist_ok=True)
PY = sys.executable


def wait_port(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.3)
    return False


def main() -> int:
    server_log = (VERIFY / "m1-server.log").open("w")
    server = subprocess.Popen([PY, str(HERE / "mock_server.py")], stdout=server_log, stderr=subprocess.STDOUT)
    try:
        if not wait_port("127.0.0.1", 8000):
            print("[run_m1] server did not open port 8000 in time", file=sys.stderr)
            return 1
        client = subprocess.run(
            [PY, str(HERE / "mock_client.py")], capture_output=True, text=True
        )
        out = client.stdout + client.stderr
        (VERIFY / "m1-client.log").write_text(out)
        print(out, end="")
        print(f"[run_m1] client exit={client.returncode}")
        return client.returncode
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
        server_log.close()


if __name__ == "__main__":
    sys.exit(main())
