# 최종 보고서 — LAB2 출처가 보이는 VLM/VLA 판단·행동 기록

> 완료: 2026-07-21 · 대상: LAB2 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

LAB1은 카메라부터 action과 outcome까지 물리 episode를 보존했지만, 화면에 “생각 과정”을 붙일 때 무엇이 실제 VLA 출력이고 무엇이 별도 VLM 관측 또는 controller 실행인지 구분할 계약이 없었다. 이 경계를 흐리면 보조 설명을 OpenVLA의 내부 생각처럼 꾸미거나 scripted 결과를 모델 능력으로 과장할 수 있다. LAB2는 direct VLA와 계층형 VLM→skill을 같은 event contract로 기록하되 실제 source와 인과 역할을 분리하는 것을 목표로 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “언어 지시를 이해하고 로봇 행동을 생성·실행하며 그 전 과정을 사람이 관찰”하는 성공 모습에서 관찰 가능성의 의미를 사실 기반으로 확장했다. 이제 모델 관측, high-level skill 선택, raw VLA action, controller 실행과 환경 결과를 서로 다른 주체로 추적할 수 있어 **이해에서 실증으로**, **데모에서 실험 플랫폼으로** 축이 함께 전진했다.

## 3. 경로 (horizon → milestone → steps)

승인된 “보고 판단하고 움직이는 로봇팔 실험실” Horizon의 두 번째 milestone으로, source/parent/assistance event 계약, 실제 direct OpenVLA emitter, local Qwen3-VL→bounded skill lane, 네 PASS/FAIL trace 통합 비교의 네 step을 실행했다. 계획대로 cloud API와 free-form chain-of-thought는 사용하지 않았다. VLM 모델은 브랜드 선호가 아니라 공개 라이선스·revision·32GB 적합성·structured output 기술 게이트로 선택했다.

## 4. 구현 결과 (무엇이 만들어졌나)

모든 판단·행동 event는 `sensor|vlm|vla|controller|environment` source, causal role, parent, component revision, payload reference와 assistance를 보존한다. Direct lane은 main-camera input에서 OpenVLA raw action과 executed action을 78-frame PASS와 220-frame FAIL 전체에서 연결했다. 별도 VLM lane은 Qwen3-VL-4B-Instruct가 실제 고정 frame을 보고 scene/skill JSON을 만들고, allowlist executor가 scripted canonical action sequence를 같은 LIBERO 초기 상태에서 실행해 PASS와 timeout을 다시 측정했다. 두 lane은 같은 모델 내부 단계가 아니며 UI가 그대로 드러낼 비교 정본이 됐다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

더 작은 Qwen2.5-VL-3B는 non-commercial-only 연구 라이선스라 공개 포트폴리오 재사용 게이트에서 제외했고, Apache-2.0인 Qwen3-VL-4B를 exact revision으로 고정했다. 첫 VLM prompt에 정답 값이 예시로 들어 있어 모델 관측과 복사를 구분할 수 없는 near-miss를 발견했고, 값 없는 schema prompt로 바꾼 뒤 시작·60번째 frame에서 서로 다른 spatial summary를 다시 얻었다. WSL 환경 생성 명령의 변수 인용 오류로 레포 안에 이름이 `\`인 임시 venv가 잠시 생겼지만 생성 직후 `pyvenv.cfg`와 경계를 확인해 그 폴더만 제거하고 `/home/yusun/.venvs/physical-ai-vlm`에 재생성했다. VLM lane의 저수준 action은 모델이 생성한 것이 아니므로 controller와 result event 모두 `scripted_skill` assistance로 명시했다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-lab2-provenance-event-contract/`, `changesets/20260721-lab2-direct-vla-causal-emitter/`, `changesets/20260721-lab2-vlm-bounded-skill-lane/`, `changesets/20260721-lab2-two-lane-comparison-evidence/`.
- Commits: `9644562`, `9d85cd0`, `4f0d0ac`, `4deb194`.
- Contract: `experiments/148-observable-decision-action-trace/event-schema.json`, semantic validator와 31개 unit/integration failure probe.
- Direct VLA: OpenVLA revision `962318cec55ac10993ff0f5f43eda9a270b4c873`; PASS 78 frames/235 events/success, FAIL 220 frames/661 events/timeout, wrist model-input false, executed action 298/298 linked.
- VLM: Qwen3-VL-4B-Instruct revision `ebb281ec70b05090aa6165b016eac8ec08e71b17`; 고정 frame 3/3 structured JSON PASS, peak GPU allocation 8,970,172,928 bytes.
- VLM→skill: PASS 78/78 scripted actions와 measured success/reward 1.0, FAIL 220/220 actions와 measured timeout/reward 0.0.
- Integration: `experiments/148-observable-decision-action-trace/verify/two-lane/comparison-report.json` 종합 PASS; 네 schema PASS, source/assistance/outcome/hidden-reasoning relabel negative gates PASS.
- Cleanup: VLM/LIBERO/OpenVLA process 0, ports 8012~8015 listener 0, GPU compute process 0, `git diff --check`와 Python compile PASS.
- 크기 회고: 승인 plan의 4개 독립 changeset으로 닫혀 선언한 `changesets>=4`와 정확히 일치하며 contract, direct producer, VLM executor, 통합 evidence가 각각 독립 검증 표면을 가진다.
- 실표면: local RTX 5090에서 Qwen3-VL exact checkpoint를 실제 image+instruction에 3회 실행하고, LIBERO에서 VLM-selected allowlist skill의 PASS 78-action과 FAIL 220-action을 실제 `env.step`으로 재실행했다.
- 재현: `python experiments/148-observable-decision-action-trace/verify_two_lane.py --direct-pass <direct-pass.json> --direct-fail <direct-fail.json> --vlm-pass <vlm-pass.json> --vlm-fail <vlm-fail.json> --output <comparison-report.json>`.

## 7. 후속 제안 (다음에 무엇을)

같은 Horizon의 LAB3에서 이 네 trace를 정적 public asset bundle로 변환하고, main/wrist camera·instruction·source-tagged timeline·raw evidence drawer가 한 화면에서 scrub되게 해야 한다. UI에는 direct VLA와 VLM→scripted skill badge, recorded simulation 경계와 assistance를 항상 노출하고 local/live Playwright QA로 5분 reviewer path를 검증한다.
