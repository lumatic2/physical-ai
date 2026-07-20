# Direct VLA vs VLM→skill comparison

같은 LIBERO task 5, dataset revision과 PASS/FAIL 초기 상태에서 서로 다른 두 제어 구조를 같은 `physical-ai-causal-events-v1` 계약으로 비교한다.

| 구분 | Direct VLA | VLM → bounded skill |
|---|---|---|
| 판단/action source | OpenVLA가 매 frame raw 7D action 제안 | Qwen3-VL이 scene JSON과 `pick_and_place` skill 선택 |
| controller | OpenVLA action 후처리 후 `env.step` | allowlist executor가 canonical action sequence replay |
| assistance | `none` | `scripted_skill` |
| 언어적 내부 생각 | 없음 | 없음 — structured observation/skill만 기록 |
| PASS | 78 frames, 235 events, success | 5 events, 78 actions, measured success |
| FAIL | 220 frames, 661 events, timeout | 5 events, 220 actions, measured timeout |

VLM lane은 Qwen3-VL이 저수준 action을 만들었다는 증거가 아니다. VLM은 high-level skill을 선택했고 별도 scripted controller가 action을 실행했다. Direct VLA lane에는 scene description을 사후 생성하지 않는다.

## 통합 게이트

`comparison-report.json`은 네 stream의 schema, 상반 outcome, model/component revision, assistance와 SHA-256을 고정한다. VLM event를 VLA thought로 바꾸거나, scripted result를 model result로 바꾸거나, assistance를 제거하거나, hidden reasoning을 추가하거나, FAIL을 PASS로 relabel하면 실패한다.

```powershell
python experiments/148-observable-decision-action-trace/verify_two_lane.py `
  --direct-pass experiments/148-observable-decision-action-trace/verify/direct-vla/pass-events.json `
  --direct-fail experiments/148-observable-decision-action-trace/verify/direct-vla/fail-events.json `
  --vlm-pass experiments/148-observable-decision-action-trace/verify/vlm-skill/vlm-skill-events.json `
  --vlm-fail experiments/148-observable-decision-action-trace/verify/vlm-skill/vlm-skill-events-fail.json `
  --output experiments/148-observable-decision-action-trace/verify/two-lane/comparison-report.json
```
