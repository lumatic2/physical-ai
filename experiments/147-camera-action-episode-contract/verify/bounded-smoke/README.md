# Bounded OpenVLA + LIBERO episode evidence

2026-07-21에 RTX 5090이 연결된 Ubuntu WSL2에서 실제 OpenVLA 추론과 LIBERO
시뮬레이션을 3 policy step으로 제한해 기록한 LeRobot v3 episode다.

## Claim boundary

- 증명하는 것: 고정 OpenVLA checkpoint가 main camera와 언어 지시를 받아 7D action을
  생성했고, LIBERO가 그 action을 실행했으며 main/wrist camera, 8D state, executed action,
  latency를 같은 episode clock에 기록했다.
- 증명하지 않는 것: 실물 로봇, live telemetry, wrist camera가 OpenVLA 입력이었다는 주장,
  과제 성공. 이 episode는 bounded timeout이므로 `success=false`가 맞다.

## Pinned inputs

- OpenVLA: `openvla/openvla-7b-finetuned-libero-spatial` commit
  `962318cec55ac10993ff0f5f43eda9a270b4c873`
  ([Hugging Face](https://huggingface.co/openvla/openvla-7b-finetuned-libero-spatial), 접근일 2026-07-21)
- LIBERO: commit `8f1084e3132a39270c3a13ebe37270a43ece2a01`
  ([GitHub](https://github.com/Lifelong-Robot-Learning/LIBERO), 접근일 2026-07-21)
- LeRobot writer source: v0.6.1 reviewed copy
  ([GitHub](https://github.com/huggingface/lerobot), 접근일 2026-07-21)
- task: `pick_up_the_black_bowl_between_the_plate_and_the_ramekin_and_place_it_on_the_plate`
- seed: `0`; policy steps: `3`; fps: `10`

## Reproduction

WSL producer:

```bash
cd experiments/01-vla-local-eval
export PYTHONPATH="$HOME/LIBERO"
export MUJOCO_GL=egl
ROOT="$(cd ../.. && pwd)/tmp/lab1-openvla-bounded-step3"
"$HOME/.venvs/vla-eval/bin/python" run.py \
  --suite libero_spatial --tasks 1 --trials 1 --seed 0 --max-policy-steps 3 \
  --ckpt-revision 962318cec55ac10993ff0f5f43eda9a270b4c873 \
  --record-root "$ROOT" --record-repo-id physical-ai/libero-openvla-bounded \
  --record-fps 10 \
  --dataset-revision 114a88f135eee21493da4863ecf411d1206b351a \
  --environment-revision 8f1084e3132a39270c3a13ebe37270a43ece2a01 \
  --port 8011
```

Official viewer export and evidence gate use the reviewed LeRobot viewer environment:

```powershell
lerobot-dataset-viz --repo-id physical-ai/libero-openvla-bounded `
  --episode-index 0 --root verify/bounded-smoke/dataset `
  --output-dir verify/bounded-smoke --batch-size 1 --num-workers 0 `
  --save 1 --display-mode rerun

python verify_bounded_evidence.py `
  --dataset-root verify/bounded-smoke/dataset `
  --sidecar verify/bounded-smoke/dataset/meta/lab_provenance/episode_000000.json `
  --rrd verify/bounded-smoke/physical-ai_libero-openvla-bounded_episode_0.rrd `
  --rerun-cli rerun --expected-frames 3 --producer-kind openvla-libero `
  --output verify/bounded-smoke/openvla-report.json
```

## Observed result

- profile: PASS; `producer_claim_ready=true`
- frames: 3; cameras: 2; state: 8D; executed action: 7D
- request latency: 1683.653 ms, 211.380 ms, 202.956 ms
- Rerun entities: main camera, wrist camera, state, action
- Rerun timelines: `frame_index`, `timestamp`; 모든 chunk sorted
- dataset tree SHA-256: `678ae0b077bda0722435c4d774f29761355fd0ca3fd9823940a8b2ddbd776774`
- RRD SHA-256: `92c3bf36aa324754278e25aca6707a0eb1b135d15bfdf2c5d175355de893ceeb`

기계 판정은 [openvla-report.json](openvla-report.json), 사람이 scrub할 파생 증거는
`physical-ai_libero-openvla-bounded_episode_0.rrd`, 시계열 정본은 `dataset/`이다.
