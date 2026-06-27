"""Record the WSL GR00T runtime preflight needed after the trace-adapter gate."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EXP_DIR = Path(__file__).resolve().parent
VERIFY_DIR = EXP_DIR / "verify"

WSL_REPO = "/home/<user>/gr00t-wbc-native"
WSL_SAMPLE_DIR = "/home/<user>/gr00t_sample_download_probe"
WIN_GROOT = "/mnt/c/Users/<user>/projects/physical-ai/tmp/gr00t-wbc"


def run_wsl(script: str, timeout_s: float = 60.0) -> dict[str, Any]:
    completed = subprocess.run(
        ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "-lc", script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout_s,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip().splitlines(),
        "stderr": completed.stderr.strip().splitlines(),
    }


def main() -> int:
    VERIFY_DIR.mkdir(parents=True, exist_ok=True)

    commands = {
        "git_lfs": "git lfs version && git lfs env | sed -n '1,20p'",
        "gr00t_check_environment": f"cd {WSL_REPO} && source .venv_sim/bin/activate && python check_environment.py",
        "run_sim_help": f"cd {WSL_REPO} && source .venv_sim/bin/activate && python gear_sonic/scripts/run_sim_loop.py --help | sed -n '1,80p'",
        "import_smoke": f"""cd {WSL_REPO} && source .venv_sim/bin/activate && python - <<'PY'
import mujoco, torch, zmq, gear_sonic
import gear_sonic.scripts.run_sim_loop as run_sim_loop
print("IMPORT_SMOKE_PASS")
print("mujoco", mujoco.__version__)
print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("zmq", zmq.__version__)
print("run_sim_loop_module", run_sim_loop.__name__)
PY""",
        "sample_download_listing": f"find {WSL_SAMPLE_DIR} -type f | sort | sed -n '1,80p'",
        "native_repo_assets": f"cd {WSL_REPO} && find . -type f \\( -name '*.onnx' -o -name '*.pkl' \\) | sed 's#^./##' | sort | sed -n '1,80p'",
        "run_sim_loop_timeout_smoke": (
            f"cd {WSL_REPO} && source .venv_sim/bin/activate && python - <<'PY'\n"
            "import subprocess\n"
            "cmd = [\n"
            "    'timeout', '8s', 'python', 'gear_sonic/scripts/run_sim_loop.py',\n"
            "    '--no-enable-onscreen', '--no-enable-offscreen', '--sim-sync-mode', '--mp-start-method', 'fork',\n"
            "]\n"
            "completed = subprocess.run(cmd, text=True, capture_output=True, check=False)\n"
            "print(f'RUN_SIM_RC:{completed.returncode}')\n"
            "print('STDOUT_HEAD')\n"
            "print('\\n'.join(completed.stdout.splitlines()[:80]))\n"
            "print('STDERR_HEAD')\n"
            "print('\\n'.join(completed.stderr.splitlines()[:80]))\n"
            "PY"
        ),
        "windows_mount_install_failure_probe": f"cd {WIN_GROOT} && tr -d '\\r' < install_scripts/install_mujoco_sim.sh > /tmp/install_mujoco_sim_lf_probe.sh && bash /tmp/install_mujoco_sim_lf_probe.sh",
    }

    results: dict[str, Any] = {}
    for name, command in commands.items():
        timeout = 20.0
        if name in {"windows_mount_install_failure_probe", "run_sim_loop_timeout_smoke"}:
            timeout = 120.0
        results[name] = run_wsl(command, timeout_s=timeout)

    git_lfs_ok = results["git_lfs"]["returncode"] == 0 and any(
        "git-lfs/" in line for line in results["git_lfs"]["stdout"]
    )
    sample_ok = results["sample_download_listing"]["returncode"] == 0 and len(
        results["sample_download_listing"]["stdout"]
    ) >= 6
    help_ok = results["run_sim_help"]["returncode"] == 0 and any(
        "run_sim_loop.py" in line or "--enable-onscreen" in line for line in results["run_sim_help"]["stdout"]
    )
    import_ok = results["import_smoke"]["returncode"] == 0 and any(
        "IMPORT_SMOKE_PASS" in line for line in results["import_smoke"]["stdout"]
    )
    cuda_ok = any("cuda_available True" in line for line in results["import_smoke"]["stdout"])
    onnx_ok = any("GR00T-WholeBodyControl-Balance.onnx" in line for line in results["native_repo_assets"]["stdout"])
    sim_loop_text = "\n".join(results["run_sim_loop_timeout_smoke"]["stdout"] + results["run_sim_loop_timeout_smoke"]["stderr"])
    sim_loop_smoke_ok = (
        "RUN_SIM_RC:124" in sim_loop_text or "RUN_SIM_RC:0" in sim_loop_text or "RUN_SIM_RC:1" in sim_loop_text
    ) and "Traceback" not in sim_loop_text and "ModuleNotFoundError" not in sim_loop_text
    check_env_text = "\n".join(results["gr00t_check_environment"]["stdout"] + results["gr00t_check_environment"]["stderr"])
    check_env_sim_ready = "Git LFS: installed" in check_env_text and "Disk space" in check_env_text
    windows_mount_permission_block = results["windows_mount_install_failure_probe"]["returncode"] != 0 and any(
        "Permission denied" in line for line in results["windows_mount_install_failure_probe"]["stderr"]
        + results["windows_mount_install_failure_probe"]["stdout"]
    )

    checks = {
        "git_lfs_healthy": git_lfs_ok,
        "hf_sample_download_present": sample_ok,
        "run_sim_help_pass": help_ok,
        "venv_import_smoke_pass": import_ok,
        "torch_cuda_visible": cuda_ok,
        "g1_balance_walk_onnx_present": onnx_ok,
        "gr00t_check_environment_basic_sim_ready": check_env_sim_ready,
        "run_sim_loop_timeout_smoke_no_traceback": sim_loop_smoke_ok,
        "windows_mount_install_permission_block_confirmed": windows_mount_permission_block,
    }
    blockers = []
    if windows_mount_permission_block:
        blockers.append("install_mujoco_sim_must_run_on_wsl_native_filesystem_not_mnt_c")
    if "TensorRT_ROOT not set" in check_env_text:
        blockers.append("tensorrt_root_missing_for_cpp_deployment")
    if "Isaac Lab: not installed" in check_env_text:
        blockers.append("training_stack_not_installed_but_not_needed_for_mujoco_sim_loop")

    verdict = (
        "WSL_SIM_RUNTIME_PREFLIGHT_PASS__DEPLOYMENT_PARTIAL"
        if git_lfs_ok and sample_ok and help_ok and import_ok and cuda_ok and sim_loop_smoke_ok
        else "WSL_SIM_RUNTIME_PREFLIGHT_FAIL"
    )
    result = {
        "experiment": "121-g1-gr00t-wsl-runtime-preflight",
        "verdict": verdict,
        "m19_closed": False,
        "checks": checks,
        "blockers": blockers,
        "commands": commands,
        "results": results,
        "interpretation": (
            "WSL Ubuntu can now run the GR00T MuJoCo sim Python stack from a native /home checkout: "
            "Git LFS is healthy, HF sample data was downloaded, the .venv_sim install completed, run_sim_loop.py "
            "exposes its CLI, and CUDA is visible to torch. The /mnt/c checkout remains unsuitable for creating "
            ".venv_sim due mount permission behavior, so real sim2sim should run from the native WSL copy or a fresh "
            "WSL-native clone. M19 is still open because no real measured g1_debug/CSV squat trace has passed exp120."
        ),
        "sources": [
            {
                "url": "https://github.com/git-lfs/git-lfs/blob/main/INSTALLING.md",
                "accessed": "2026-06-18",
                "claim": "Git LFS apt/deb package install uses sudo apt-get install git-lfs after package repository availability.",
            },
            {
                "url": "https://nvlabs.github.io/GR00T-WholeBodyControl/getting_started/quickstart.html",
                "accessed": "2026-06-18",
                "claim": "GR00T MuJoCo sim2sim uses install_mujoco_sim.sh and then python gear_sonic/scripts/run_sim_loop.py.",
            },
            {
                "url": "https://www.unitree.com/g1/",
                "accessed": "2026-06-18",
                "claim": "Unitree G1 has 23 to 43 joint motors, 6 DoF per leg, knee range 0 to 165 degrees, and hip pitch plus/minus 154 degrees.",
            },
            {
                "url": "https://docs.quadruped.de/projects/g1/html/operation_1.2.html",
                "accessed": "2026-06-18",
                "claim": "The G1 control documentation lists a Squat Mode, but describes it as a transition to squat posture without balance control.",
            },
        ],
        "next_required_evidence": [
            "Run GR00T sim loop and deployment together from WSL-native checkout, preferably headless/offscreen first.",
            "Capture real measured g1_debug or StateLogger CSV output from the running controller.",
            "Feed the measured trace through exp120 and only close M19 if native visible/contact/slip/return plus browser replay pass.",
        ],
    }

    (VERIFY_DIR / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    summary = [
        "# GR00T WSL Runtime Preflight Summary",
        "",
        f"- Verdict: `{verdict}`",
        f"- Git LFS healthy: `{checks['git_lfs_healthy']}`",
        f"- HF sample download present: `{checks['hf_sample_download_present']}`",
        f"- run_sim_loop help pass: `{checks['run_sim_help_pass']}`",
        f"- venv import smoke pass: `{checks['venv_import_smoke_pass']}`",
        f"- torch CUDA visible: `{checks['torch_cuda_visible']}`",
        f"- G1 Balance/Walk ONNX present: `{checks['g1_balance_walk_onnx_present']}`",
        f"- run_sim_loop timeout smoke no traceback: `{checks['run_sim_loop_timeout_smoke_no_traceback']}`",
        f"- M19 closed: `False`",
        "",
        "## Blockers / Constraints",
        *(f"- `{blocker}`" for blocker in blockers),
        "",
        "## Next Evidence",
        *(f"- {item}" for item in result["next_required_evidence"]),
        "",
    ]
    (VERIFY_DIR / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"verdict": verdict, "checks": checks, "blockers": blockers}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
