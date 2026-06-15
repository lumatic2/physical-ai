# experiments/

손으로 직접 짜보는 작은 구현들. 각 실험은 `<NN>-<slug>/README.md` 4섹션 형식 —
템플릿: [EXPERIMENT_TEMPLATE.md](EXPERIMENT_TEMPLATE.md).

## 인덱스

| # | 슬러그 | 가설 (한 줄) | 결과 |
|---|--------|-------------|------|
| 01 | [vla-local-eval](01-vla-local-eval/README.md) | RTX 5090서 OpenVLA 7B REST 추론 → LIBERO success rate > 0 | ✅ H1 15.1GB · H2 168ms · H3 73%(11/15) |
| 02 | [action-repr-bench](02-action-repr-bench/README.md) | 같은 libero_spatial서 π0.5(flow-matching chunk)가 OpenVLA(이산토큰)와 비교 가능한 SR | ✅ matched 3task: π0.5 **98.7%**(148/150) vs OpenVLA 73.3%(11/15), Fisher p<1e-3 |
| 03 | [digital-twin](03-digital-twin/README.md) | 하드웨어 없이 SO-100을 sim에 세우고 정책 롤아웃을 웹에서 인터랙티브로 보여줄 수 있다 | ✅ 트윈 [라이브](https://physical-ai-arm.askewly.com) + scripted pick-and-place **3단 스택** replay(IK 0.1mm). **+ Go1 live 학습정책**(`?exp=go1-walk`, onnxruntime-web closed-loop, exp04 정책). **+ M9 인터랙티브 텔레옵**(키보드 WASD 보행 조종 + 마우스 EE IK 텔레옵, 로컬 QA PASS). ADR [0004](../docs/adr/0004-digital-twin-stack.md)·[0005](../docs/adr/0005-learned-policy-sandbox.md) |
| 04 | [go1-rl-walk](04-go1-rl-walk/README.md) | RTX5090서 Playground Go1 joystick 정책을 직접 학습→ONNX→native mujoco에서 N초 안 넘어지고 보행 | ✅ 학습 8.8분(reward→29.7), onnx parity 4.8e-6, native 12s·11.8m·0.99m/s 보행. ADR [0005](../docs/adr/0005-learned-policy-sandbox.md) 단계 1 |
| 05 | [g1-rl-walk](05-g1-rl-walk/README.md) | RTX5090서 Playground G1 휴머노이드 joystick 정책 학습→ONNX→native→웹 live closed-loop (M8, gait phase clock) | ✅ 학습 46.5분(reward −6.4→14.8), onnx parity 2.1e-6, native 12s·9.38m·0.78m/s, 번들 byte-parity 0.0, 라이브 `?exp=g1-walk`(5.0m·0 에러). ADR [0005](../docs/adr/0005-learned-policy-sandbox.md) |
| 06 | [spot-rl-walk](06-spot-rl-walk/README.md) | RTX5090서 Playground Spot 4족 joystick 정책 학습→ONNX→native→웹 byte-parity 보행 (M11, Go1↔Spot 비교) | ✅ 학습 6.5분(reward 30.6), onnx parity 4.07e-6, native 12s·11.1m·0.92m/s, **웹 byte-parity 2.91e-7**·라이브 `?exp=spot-walk`. 학습정책 3종(Go1·G1·Spot) |
| 07 | [command-terrain-robustness](07-command-terrain-robustness/README.md) | Go1·Spot 정책이 forward 외 strafe/turn/diagonal 및 rough terrain에서도 버티는지 측정 | ✅ 로컬+라이브 flat/rough command sweep PASS. live `go1-rough-walk`, `spot-rough-walk` 재현 가능 |
| 08 | [policy-expansion](08-policy-expansion/README.md) | G1 rough 변형을 새 policy package처럼 흡수해 플랫폼 반복성을 검증 | ✅ native byte-parity 0.0, WASM load OK, 로컬+라이브 G1 rough command sweep PASS, Go1/G1/Spot 회귀 PASS |
| 09 | [real-arm-gate](09-real-arm-gate/README.md) | M7 실물 도달 전에 SO-101 구매/조립/ACT 경로를 닫을 수 있는지 판단 | 🟨 게이트 패키지 완료: SO-101 leader+follower + ACT-first 추천, 실제 구매는 외부 입력 필요 |
| 10 | [barkour-rl-walk](10-barkour-rl-walk/README.md) | Barkour Playground policy를 새 학습부터 ONNX/native/web/live QA까지 end-to-end로 흡수할 수 있는지 검증 | ✅ 학습 6.5분(reward 1.76→38.25), ONNX parity 2.95e-6, native/web/live QA PASS, live `?exp=barkour-walk` |
| 11 | [policy-addition-routine](11-policy-addition-routine/README.md) | 새 policy 추가가 매번 bespoke 작업이 아니라 체크 가능한 운영 루틴인지 검증 | ✅ `POLICY_ADDITION.md` + `check_policy_bundle.py`, 현재 policy 7종 PASS |
| 12 | [policy-gallery-comparison](12-policy-gallery-comparison/README.md) | 정책 갤러리를 같은 command sweep protocol로 비교 가능한 실험판으로 만들 수 있는지 검증 | ✅ 6개 sweep report 통합, failures=0, [비교표](12-policy-gallery-comparison/verify/policy-gallery-report.md) |
| 13 | [acrobatic-feasibility](13-acrobatic-feasibility/README.md) | Atlas식 물구나무·덤블링·축구 skill을 현 G1 스택으로 바로 학습 가능한지 판단 | ✅ G1 static gate PASS: squat/front kick는 go, handstand는 hand-floor contact 부재로 blocked, tumble은 reference motion 필요 |
| 14 | [skill-authoring](14-skill-authoring/README.md) | 원하는 동작을 versioned behavior spec으로 고정해 reward/scene/metric으로 번역할 수 있는지 검증 | ✅ 4개 G1 skill spec compile PASS, failed=0, M19/M21/M22 입력 계약 생성 |
| 15 | [g1-skill-baseline](15-g1-skill-baseline/README.md) | `g1_squat` compiled spec이 native G1 position-control baseline으로 안정적인지 검증 | 🟥 scripted baseline FAIL: hold/mild/deep 모두 1.24~1.25초 fall, balance reward wrapper 필요 |
| 16 | [ball-skill-sandbox](16-ball-skill-sandbox/README.md) | 축구/라보나슛 전 단계로 G1+ball scene과 ball distance/direction metric을 만들 수 있는지 검증 | ✅ scene load + ball metric PASS: injected ball distance 0.862m, direction error 0.000rad |

## 실행 원칙
- mock 먼저, real 다음 (비용·시간 절약 + 가설 격리)
- `verify/` 폴더에 raw 출력 박제 (재현성)
- 통찰 섹션 비면 실험이 안 끝난 것
