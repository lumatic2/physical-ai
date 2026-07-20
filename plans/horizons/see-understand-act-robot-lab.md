# HORIZON — 보고 판단하고 움직이는 로봇팔 실험실

> 생성: 2026-07-20 · ROADMAP marker: `harness:goal id="see-understand-act-robot-lab"` · 상태: active
> 위계: Objective(`OBJECTIVE.md`) → **Horizon**(이 문서) → Milestone(`plans/2026-07-20-lab*-*.md`) → Step.
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
| **LAB1** | 카메라-행동 episode 계약 — producer/schema/canonical evidence의 독립 step과 통합 검증 | `plans/2026-07-20-lab1-camera-action-episode-contract.md` | 일괄승인 2026-07-20 | `research/2026-07-20-see-understand-act-robot-lab-architecture.md` |
| **LAB2** | 출처가 보이는 VLM/VLA 판단·행동 기록 — semantic/VLA/controller lane과 인과 검증 | `plans/2026-07-20-lab2-observable-decision-action-trace.md` | 일괄승인 2026-07-20 | `research/2026-07-20-see-understand-act-robot-lab-architecture.md` |
| **LAB3** | 공개 로봇팔 실험실 — dual-camera UI, timeline replay, local/live evidence 통합 | `plans/2026-07-20-lab3-public-robot-arm-laboratory.md` | 일괄승인 2026-07-20 | `research/2026-07-20-see-understand-act-robot-lab-architecture.md` |

## 닫는 기준

- canonical PASS와 FAIL episode가 main/wrist camera, state, instruction, action, latency, outcome을 같은 versioned trace로 보존한다. — 관측: LAB1 validator와 `experiments/147-camera-action-episode-contract/verify/`.
- 공개 trace의 모든 event가 `sensor|vlm|vla|controller|environment` source를 갖고 보조 설명과 실제 action의 인과 경계를 구분한다. — 관측: LAB2 provenance validator와 negative fixture.
- 공개 브라우저에서 main scene, wrist model-input view, instruction, decision/action/result timeline을 scrub할 수 있고 raw evidence로 내려갈 수 있다. — 관측: LAB3 local/live Playwright smoke와 `qaArmLabSummary()`.
- `recorded evidence`를 live inference로, simulation을 real telemetry로 표시하는 fixture가 QA에서 실패한다. — 관측: claim-boundary negative smoke.
- 세 Milestone DoD와 Horizon 통합 5분 reviewer checklist가 모두 PASS한다.

## 미리 쓰는 실패 회고

- **예쁜 동영상만 남고 정책 실행과 연결되지 않았다.** → 예방: LAB1 trace가 timestep·policy/environment revision·raw action을 의무화하고 LAB3 UI event가 raw artifact를 가리킨다.
- **보조 VLM 설명을 VLA의 생각으로 꾸며 신뢰를 잃었다.** → 예방: LAB2 source enum과 hidden reasoning 금지 fixture를 DoD로 둔다.
- **새 모델 학습과 상시 backend에 빠져 공개 화면을 못 만들었다.** → 예방: 공개 checkpoint·단일 과제·recorded evidence를 Horizon 범위로 고정하고 persistent GPU backend는 제외한다.

## Objective 임팩트

- close 시 기록: 관찰 가능한 피지컬 AI 실험실이 Objective의 성공 모습과 움직이는 축을 얼마나 충족했는지 선언/실측으로 대조한다.

## 링크

- 위(Objective): `OBJECTIVE.md`
- 설계 결정: `docs/adr/0013-observable-vision-language-action-lab.md`
- 아래(Milestone PLANs): `plans/2026-07-20-lab1-camera-action-episode-contract.md`, `plans/2026-07-20-lab2-observable-decision-action-trace.md`, `plans/2026-07-20-lab3-public-robot-arm-laboratory.md`
