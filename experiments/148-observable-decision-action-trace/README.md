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
