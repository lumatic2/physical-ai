# HORIZON — 보고 판단하고 움직이는 로봇팔 실험실

> 생성: 2026-07-20 · 완료: 2026-07-21 · ROADMAP marker: `harness:goal id="see-understand-act-robot-lab"` · 상태: completed
> 위계: Objective(`OBJECTIVE.md`) → **Horizon**(이 문서) → Milestone(`plans/2026-07-21-lab*-*.md`) → Step.
> 진행 상태의 정본은 `ROADMAP.md` marker다.

## 목표

- 카메라·센서·언어 지시가 로봇 행동으로 변환되는 과정을 episode evidence와 브라우저 UI에서 관찰·재생·검증 가능한 대표 피지컬 AI 제품으로 만든다.
- Objective의 **이해에서 실증으로**, **데모에서 실험 플랫폼으로** 축을 한 번에 전진시킨다.
- **무감독 분량: 승인 후 최소 3 무감독 세션**

## 왜 지금

- 이전 Horizon은 scenario, contact, randomized episode와 evidence contract를 닫았지만 대표 화면은 여전히 로봇·환경 갤러리로 읽힌다.
- LIBERO VLA evaluator는 이미 camera+instruction→action→environment loop를 실행하지만 camera/state/action/outcome이 같은 관찰 가능한 trace로 남지 않는다.
- 사용자가 특정 로봇 제조사보다 VLM/VLA가 보고 판단하고 움직이는 과정을 이해할 수 있는 실험실을 대표 결과물로 명시했다.

## 담을 milestone — 설계 번들 인덱스

| milestone | 제목 (왜 milestone 규모인가) | plan doc | 승인 | 리서치 입력 |
|---|---|---|---|---|
| **LAB1** | LeRobot episode 증거 — canonical profile/writer/PASS·FAIL/Rerun의 독립 step과 통합 검증 | `plans/2026-07-21-lab1-lerobot-episode-evidence.md` | Horizon 일괄승인 2026-07-21 | 기존 architecture/GitHub research + `experiments/147-camera-action-episode-contract/verify/official-viewer-reuse/README.md` |
| **LAB2** | 관찰 가능한 판단·행동 인과 기록 — direct VLA와 VLM→skill lane의 사실 기반 비교 | `plans/2026-07-21-lab2-observable-causal-trace.md` | Horizon 일괄승인 2026-07-21 | LAB1 canonical episode + 기존 architecture/GitHub research |
| **LAB3** | 공개 관찰형 로봇팔 실험실 — 공식 viewer interaction 선택 이식과 local/live evidence 통합 | `plans/2026-07-21-lab3-public-observable-arm-lab.md` | Horizon 일괄승인 2026-07-21 | official viewer reuse evidence + LAB2 causal trace |

## 닫는 기준

- canonical PASS와 FAIL episode가 main/wrist camera, state, instruction, action, latency, outcome을 LeRobot v3 episode와 provenance sidecar로 보존한다. — 관측: LAB1 profile validator, 공식 Rerun export와 `experiments/147-camera-action-episode-contract/verify/`.
- 공개 trace의 모든 event가 `sensor|vlm|vla|controller|environment` source를 갖고 보조 설명과 실제 action의 인과 경계를 구분한다. — 관측: LAB2 provenance validator와 negative fixture.
- 공개 브라우저에서 main scene, wrist model-input view, instruction, decision/action/result timeline을 scrub할 수 있고 raw evidence로 내려갈 수 있다. — 관측: LAB3 local/live Playwright smoke와 `qaArmLabSummary()`.
- `recorded evidence`를 live inference로, simulation을 real telemetry로 표시하는 fixture가 QA에서 실패한다. — 관측: claim-boundary negative smoke.
- 세 Milestone DoD와 Horizon 통합 5분 reviewer checklist가 모두 PASS한다.

## 미리 쓰는 실패 회고

- **예쁜 동영상만 남고 정책 실행과 연결되지 않았다.** → 예방: LAB1 trace가 timestep·policy/environment revision·raw action을 의무화하고 LAB3 UI event가 raw artifact를 가리킨다.
- **보조 VLM 설명을 VLA의 생각으로 꾸며 신뢰를 잃었다.** → 예방: LAB2 source enum과 hidden reasoning 금지 fixture를 DoD로 둔다.
- **새 모델 학습과 상시 backend에 빠져 공개 화면을 못 만들었다.** → 예방: 공개 checkpoint·단일 과제·recorded evidence를 Horizon 범위로 고정하고 persistent GPU backend는 제외한다.

## Objective 임팩트

- **이해에서 실증으로:** 실제 OpenVLA와 Qwen3-VL/LIBERO 실행을 camera·state·action·outcome과 source-tagged event로 고정해 단일 과제의 판단·행동을 재현 가능한 증거로 만들었다.
- **데모에서 실험 플랫폼으로:** `https://robotics.askewly.com/arm-lab`에서 dual-camera, playback, causal timeline, raw evidence를 직접 검토하는 공개 제품 표면을 만들었다(접근·live QA 2026-07-21).
- **시뮬레이션에서 실물로:** recorded simulation과 real telemetry의 경계는 강화했지만 실물 축 자체는 움직이지 않았다. 다음 실물 Horizon까지 이 한계를 유지한다.
- **분량 대조:** 구 선언은 최소 3 무감독 세션이었고 실측은 LAB1~LAB3 합계 12 changeset·6 session token이다. 선언 단위와 현행 changeset 단위가 달라 직접 판정은 불가하며, 다음 Horizon부터 bottom-up 합산한 ≥25 changeset을 사용한다.
- **닫는 기준 판정:** LAB1 canonical episode, LAB2 provenance event, LAB3 public reviewer gate와 claim-boundary negative smoke가 모두 PASS해 Horizon을 완료한다.

## 링크

- 위(Objective): `OBJECTIVE.md`
- 설계 결정: `docs/adr/0013-observable-vision-language-action-lab.md`
- 아래(Milestone PLANs, Horizon 일괄승인 2026-07-21): `plans/2026-07-21-lab1-lerobot-episode-evidence.md`, `plans/2026-07-21-lab2-observable-causal-trace.md`, `plans/2026-07-21-lab3-public-observable-arm-lab.md`
- 이전 승인 이력: `plans/2026-07-20-lab1-camera-action-episode-contract.md`, `plans/2026-07-20-lab2-observable-decision-action-trace.md`, `plans/2026-07-20-lab3-public-robot-arm-laboratory.md`
