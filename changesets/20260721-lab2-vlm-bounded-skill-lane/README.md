# 20260721-lab2-vlm-bounded-skill-lane

## Target

- ROADMAP milestone: LAB2 — 출처가 보이는 VLM/VLA 판단·행동 기록.
- Plan leaf: `plans/2026-07-21-lab2-observable-causal-trace.md` step-3.
- Goal: local open-weight VLM의 schema-valid 장면 관측·skill 선택을 allowlist executor와 실제 LIBERO 결과까지 연결한다.

## Planning Gate

```yaml
planning_gate:
  team_validation_mode: manual-pass
  scope_posture: selective
  delegation_decision:
    remote_background_agents: skip
    reason: "단일 32GB GPU에서 모델 probe와 LIBERO replay를 순차 실행해야 하며 병렬 GPU 작업은 충돌한다."
    target_roles: []
    execution_path: local_manual
  model_gate:
    selected: "Qwen/Qwen3-VL-4B-Instruct@ebb281ec70b05090aa6165b016eac8ec08e71b17"
    reason: "Apache-2.0, public/ungated, 4.44B parameters, official Transformers image input을 충족한다."
    rejected: "Qwen2.5-VL-3B-Instruct — qwen-research non-commercial license라 공개 포트폴리오 재사용 경계에 불리하다."
  perspectives:
    product: "VLM이 본 장면과 선택한 skill만 보여주고 모델 내부 reasoning은 저장하지 않는다."
    architecture: "VLM은 allowlist skill만 선택하고 controller action은 별도 executor가 생성한다."
    security: "클라우드 API와 secret 없이 local checkpoint를 exact revision으로 실행한다."
    qa: "malformed JSON, unknown object/target, allowlist 밖 skill을 실행 전에 차단한다."
    skeptic: "canonical action replay 도움을 scripted_skill assistance로 공개하고 VLM 자체 제어로 과장하지 않는다."
  dod:
    - "고정 main-camera frame에서 local VLM structured output이 schema를 통과한다."
    - "selected skill이 allowlist executor를 거쳐 실제 LIBERO measured outcome에 연결된다."
    - "모든 controller/result event가 scripted assistance를 명시한다."
```

## Verification

- [x] Qwen3-VL exact revision local structured output: 고정 frame 2/2 PASS.
- [x] VLM parser와 skill allowlist: LAB2 전체 25/25 tests PASS.
- [x] Same task/init LIBERO skill execution: 78/78 actions, success, reward 1.0 measured.
- [x] VLM→skill→controller→environment: 5-event source/parent/assistance chain PASS.
- [x] GPU/process cleanup, Python compile와 `git diff --check` PASS.

## Result

- Status: completed 2026-07-21
- Evidence: `experiments/148-observable-decision-action-trace/verify/vlm-skill/`.
- Near-miss: 첫 prompt에 정답 값이 들어 있어 복사와 시각 관측을 구분할 수 없었다. 값 없는 schema prompt로 교체하고 시작/60번째 frame을 재실행해 변화된 spatial summary를 확인했다.
- Reviewer verdict: VLM은 scene/skill만 생성했고 78개 저수준 action은 scripted canonical replay가 만들었다. event와 claim boundary가 이 assistance를 숨기지 않는다.
