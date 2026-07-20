# Local VLM → bounded skill evidence

Qwen3-VL-4B-Instruct를 로컬 RTX 5090에서 exact revision으로 실행해, LAB1 main-camera frame과 언어 지시에서 structured scene/skill JSON을 생성했다. 이 출력은 OpenVLA의 숨은 생각이 아니라 별도 auxiliary VLM lane이다.

## 모델 게이트

- 선택: `Qwen/Qwen3-VL-4B-Instruct@ebb281ec70b05090aa6165b016eac8ec08e71b17`.
- 이유: public/ungated, Apache-2.0, 4.44B parameters, official Transformers image-text inference 지원.
- measured peak GPU allocation: 8,970,172,928 bytes로 32,607 MiB GPU 한도 안이다.
- 제외: Qwen2.5-VL-3B-Instruct는 더 작지만 `qwen-research`의 non-commercial-only 조건 때문에 공개 포트폴리오 재사용 게이트에서 제외했다.

공식 근거: [Qwen3-VL-4B-Instruct model card](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct), [Qwen3-VL code](https://github.com/QwenLM/Qwen3-VL), [Qwen2.5-VL-3B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct) (접근일 2026-07-21).

## 실제 관측과 실행

- 시작 frame: “black bowl이 ramekin 위에 있고 plate가 근처”라는 관측, `pick_and_place(black_bowl, plate)`, confidence 0.95, 4,500.666 ms.
- 60번째 frame: gripper가 ramekin/bowl 근처에 있다는 변화된 관측, 같은 skill, confidence 0.90, 4,103.460 ms.
- executor: allowlist binding을 `canonical_action_replay`로 해석하고 same task 5/init-state 0에서 78 actions를 실제 LIBERO environment에 실행했다.
- measured result: success, reward 1.0, 78/78 actions, 10,961.653 ms.
- canonical FAIL init-state에서도 같은 local VLM decision을 검증한 뒤 220/220 scripted actions를 실행했고 timeout, reward 0.0을 측정했다.
- assistance: controller와 environment result 모두 `scripted_skill`로 표시한다. VLM이 저수준 action을 생성했다는 주장이 아니다.
- VLM skill event stream SHA-256: `b9d63ab3a4c8625050ba68e473cd01be9d67aeab8f4b28360d7b82a88159bde4`.

## 증거

- `model-gate.json`: 후보·revision·license·memory 기술 게이트.
- `frames/`: LAB1 canonical video에서 추출한 고정 main-camera frame.
- `vlm-decision-start.json`, `vlm-decision-mid.json`: raw output, parsed decision, latency, prompt/image hash.
- `vlm-decision-fail.json`: canonical FAIL 초기 frame의 structured output.
- `skill-result.json`: allowlisted executor의 실제 action source와 measured LIBERO outcome.
- `skill-result-fail.json`: 220-action timeout measured outcome.
- `vlm-skill-events.json`, `vlm-skill-report.json`: source/parent/assistance가 검증된 5-event chain.

## 재현

```bash
/home/yusun/.venvs/physical-ai-vlm/bin/python experiments/148-observable-decision-action-trace/vlm_runner.py \
  --model Qwen/Qwen3-VL-4B-Instruct \
  --revision ebb281ec70b05090aa6165b016eac8ec08e71b17 \
  --image experiments/148-observable-decision-action-trace/verify/vlm-skill/frames/pass-main-000.png \
  --instruction 'pick up the black bowl on the ramekin and place it on the plate' \
  --output <vlm-decision.json>
```

LIBERO 실행은 `skill_executor.py --vlm-record <decision> --dataset-root <LAB1 pass dataset> --sidecar <LAB1 pass sidecar> --result <result> --events <events> --report <report>`로 재현한다.
