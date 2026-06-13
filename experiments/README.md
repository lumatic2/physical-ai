# experiments/

손으로 직접 짜보는 작은 구현들. 각 실험은 `<NN>-<slug>/README.md` 4섹션 형식 —
템플릿: [EXPERIMENT_TEMPLATE.md](EXPERIMENT_TEMPLATE.md).

## 인덱스

| # | 슬러그 | 가설 (한 줄) | 결과 |
|---|--------|-------------|------|
| 01 | [vla-local-eval](01-vla-local-eval/README.md) | RTX 5090서 OpenVLA 7B REST 추론 → LIBERO success rate > 0 | ✅ H1 15.1GB · H2 168ms · H3 73%(11/15) |
| 02 | [action-repr-bench](02-action-repr-bench/README.md) | 같은 libero_spatial서 π0.5(flow-matching chunk)가 OpenVLA(이산토큰)와 비교 가능한 SR | ✅ matched 3task: π0.5 **98.7%**(148/150) vs OpenVLA 73.3%(11/15), Fisher p<1e-3 |
| 03 | [digital-twin](03-digital-twin/README.md) | 하드웨어 없이 SO-100을 sim에 세우고 정책 롤아웃을 웹에서 인터랙티브로 보여줄 수 있다 | ✅ 트윈 [라이브](https://physical-ai-arm.askewly.com) + scripted pick-and-place **3단 스택** replay(mp4+웹, IK 0.1mm, 385프레임). ADR [0004](../docs/adr/0004-digital-twin-stack.md) |
| 04 | [go1-rl-walk](04-go1-rl-walk/README.md) | RTX5090서 Playground Go1 joystick 정책을 직접 학습→ONNX→native mujoco에서 N초 안 넘어지고 보행 | ✅ 학습 8.8분(reward→29.7), onnx parity 4.8e-6, native 12s·11.8m·0.99m/s 보행. ADR [0005](../docs/adr/0005-learned-policy-sandbox.md) 단계 1 |

## 실행 원칙
- mock 먼저, real 다음 (비용·시간 절약 + 가설 격리)
- `verify/` 폴더에 raw 출력 박제 (재현성)
- 통찰 섹션 비면 실험이 안 끝난 것
