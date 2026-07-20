# Direct VLA causal evidence

LAB1 canonical PASS/FAIL dataset에서 direct OpenVLA lane을 결정적으로 파생했다. 이 기록은 언어적 “생각”을 만들지 않고 실제 main-camera model input, raw 7D policy output, controller가 받은 executed 7D action, measured latency와 environment outcome만 연결한다. wrist camera는 observer-only이며 `model_input=false`다.

## 결과

- PASS: 78 frames, 235 events, executed action 78/78 linked, wrist model input false.
- FAIL: 220 frames, 661 events, executed action 220/220 linked, wrist model input false.
- PASS stream SHA-256: `a2afe5bc5ae3a75cd0970082a10141017eef4b98df4973a18ce863cb2cd66c1b`.
- FAIL stream SHA-256: `d22e461f0dbdd28a4c1003cd42d274850d48130679cad06b55ad7ddd23518a57`.
- Claim boundary: recorded direct OpenVLA inference in LIBERO simulation; no language reasoning or real telemetry.

각 controller execution은 같은 frame의 VLA proposal 하나만 parent로 가지며, executed action의 float32 SHA-256이 LAB1 sidecar와 일치해야 한다. raw action drift, executed action drift, wrist camera model-input relabel, 실행되지 않은 proposal과 outcome relabel은 validator가 거부한다.

## 재현

```powershell
python experiments/148-observable-decision-action-trace/direct_vla.py `
  --dataset-root experiments/147-camera-action-episode-contract/verify/canonical/pass/dataset `
  --sidecar experiments/147-camera-action-episode-contract/verify/canonical/pass/dataset/meta/lab_provenance/episode_000000.json `
  --output experiments/148-observable-decision-action-trace/verify/direct-vla/pass-events.json `
  --report experiments/148-observable-decision-action-trace/verify/direct-vla/pass-report.json
```

FAIL은 위 명령의 `pass` 경로를 `fail`로 바꿔 실행한다.
