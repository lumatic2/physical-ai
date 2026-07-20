# Canonical OpenVLA + LIBERO PASS/FAIL pair

LAB1의 최종 증거는 동일한 로봇 과제와 모델 조건에서 초기 상태만 다른 실제 성공·실패 episode 두 개다. 둘 다 OpenVLA가 LIBERO 시뮬레이션을 제어하며 기록한 LeRobot v3 dataset이고, main/wrist camera, 8차원 state, 7차원 action, instruction, latency와 outcome을 보존한다.

## 고정 조건과 결과

- Suite/task: `libero_spatial`, task 5 — `pick_up_the_black_bowl_on_the_ramekin_and_place_it_on_the_plate`.
- 공통 조건: seed 0, max policy steps 220.
- OpenVLA revision: `962318cec55ac10993ff0f5f43eda9a270b4c873`.
- LIBERO revision: `8f1084e3132a39270c3a13ebe37270a43ece2a01`.
- PASS: init-state 0, success, 78 frames.
- FAIL: init-state 1, timeout, 220 frames.
- Claim boundary: recorded OpenVLA inference in LIBERO simulation; real robot telemetry나 live inference UI가 아니다.

## 증거 경로

- `pass/dataset/`, `fail/dataset/`: 독립 LeRobot v3 datasets.
- `pass/*.rrd`, `fail/*.rrd`: official `lerobot-dataset-viz`에서 만든 Rerun recordings.
- `pair-report.json`: 두 episode의 공통 contract, 상반 outcome, raw-action 연결과 SHA-256 검증 결과.

Pair gate는 outcome relabel, task/seed/revision drift, raw action과 executed action의 연결 누락을 거부한다. PASS dataset tree hash는 `fa32a6cc199cab3c77267b193f7bfac8cad20e4b0a2d25e54808d4dc786d705d`, FAIL은 `dd84f5e677a24ffa1746c70acaa6afa943817104eb00cf90fa4c6a013dda4d90`이다.

## 재현

```powershell
python experiments/147-camera-action-episode-contract/verify_canonical_pair.py `
  --pass-dataset-root experiments/147-camera-action-episode-contract/verify/canonical/pass/dataset `
  --pass-sidecar experiments/147-camera-action-episode-contract/verify/canonical/pass/dataset/meta/lab_provenance/episode_000000.json `
  --pass-rrd experiments/147-camera-action-episode-contract/verify/canonical/pass/physical-ai_libero-openvla-task5-candidate-0_episode_0.rrd `
  --fail-dataset-root experiments/147-camera-action-episode-contract/verify/canonical/fail/dataset `
  --fail-sidecar experiments/147-camera-action-episode-contract/verify/canonical/fail/dataset/meta/lab_provenance/episode_000000.json `
  --fail-rrd experiments/147-camera-action-episode-contract/verify/canonical/fail/physical-ai_libero-openvla-task5-candidate-1_episode_0.rrd `
  --rerun-cli <rerun.exe> `
  --output experiments/147-camera-action-episode-contract/verify/canonical/pair-report.json
```

저장·재생 형식은 [LeRobot dataset source](https://github.com/huggingface/lerobot/blob/main/src/lerobot/datasets/lerobot_dataset.py)와 [Rerun integration documentation](https://huggingface.co/docs/lerobot/en/visualize_datasets)를 따른다(접근일 2026-07-21).
