# 148 — Observable Decision/Action Trace

LAB2는 LAB1의 물리 episode를 바꾸지 않고, 관측·모델 출력·controller 실행·환경 결과를 실제 출처와 parent로 연결하는 파생 event stream을 만든다.

## Event contract

모든 event는 `sensor|vlm|vla|controller|environment` 중 하나의 source, `observation|decision|proposal|execution|result` causal role, 이전 parent event, pinned model/component revision, LAB1 payload reference와 assistance 표식을 갖는다. direct VLA와 VLM→skill은 별도 lane이며, structured observation이나 skill selection을 VLA의 숨은 생각으로 표시하지 않는다.

```powershell
python test_event_schema.py
python event_schema.py fixtures/valid-direct-vla-events.json
python event_schema.py fixtures/invalid-hidden-reasoning.json
```

첫 명령과 valid fixture는 exit 0이어야 한다. hidden reasoning fixture는 exit 1이어야 한다.

## Direct VLA emitter

`direct_vla.py`는 LAB1 LeRobot action Parquet과 provenance sidecar를 읽어 main-camera model input, OpenVLA raw action, controller acceptance/executed action, episode outcome을 parent chain으로 파생한다. wrist camera는 관찰용으로 남기고 model input으로 표시하지 않는다.

```powershell
python direct_vla.py --dataset-root <lerobot-root> --sidecar <episode-sidecar.json> --output <events.json> --report <report.json>
```

## Local VLM → bounded skill

`vlm_runner.py`는 pinned local Qwen3-VL checkpoint가 main-camera frame과 instruction에서 scene/skill JSON만 생성하게 한다. `skill_executor.py`는 allowlist에 등록된 binding만 받아 same-task LIBERO에서 canonical action sequence를 scripted skill로 재실행한다. 이 lane은 direct VLA와 별도이며, controller와 outcome event에 `assistance.source=scripted_skill`을 표시한다.

## Two-lane evidence

[통합 비교 evidence](verify/two-lane/README.md)는 direct OpenVLA와 auxiliary Qwen3-VL→scripted skill의 실제 PASS/FAIL 네 trace를 같은 schema로 검증한다. source relabel, assistance 누락, hidden reasoning과 outcome drift는 통합 gate가 거부한다.
