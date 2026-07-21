# Horizon Candidates — physical-ai

> Horizon 우선순위는 사용자 소유다. 선택되지 않은 후보의 아래 나열 순서는 우선순위를 뜻하지 않는다.

## 선택됨

1. **보고 판단하고 움직이는 로봇팔 실험실** (`see-understand-act-robot-lab`)
   - 선택: 2026-07-20 사용자 승인
   - 이유: camera/state/instruction이 action과 결과로 이어지는 과정을 사람이 관찰할 수 있는 대표 피지컬 AI 제품을 만든다.
   - 상태: completed 2026-07-21
2. **여러 과제에서 통하는 로봇 판단 실험실** (`multitask-generalization-lab`)
   - 선택: 2026-07-21 사용자 승인
   - 이유: 단일 성공 데모를 넘어 사전 고정한 여러 과제·초기 상태에서 두 정책을 같은 증거 계약으로 비교하고 실패 양상을 공개한다.
   - 상태: active-approved — 3-Horizon 연쇄 1/3
3. **지시를 바꿔 실행하는 로컬 피지컬 AI 실험실** (`live-instruction-execution-lab`)
   - 선택: 2026-07-21 사용자 승인
   - 이유: recorded replay를 넘어 지원 과제의 언어 지시와 정책을 선택해 실제 local GPU inference·행동·관찰 stream을 실행한다.
   - 상태: active-planning — 3-Horizon 연쇄 2/3; current approval pending after VLM lane strengthening
4. **시뮬레이션과 실물을 잇는 SO-101 검증** (`sim-real-so101-evidence-loop`)
   - 선택: 2026-07-21 사용자 승인
   - 이유: 동일한 camera/state/action/outcome 계약을 SO-101 leader/follower·dual-camera·실물 정책 평가에 연결한다.
   - 상태: queued-approved — 3-Horizon 연쇄 3/3; hardware external gate

## 승인 연쇄

1. `multitask-generalization-lab` — 25 changeset
2. `live-instruction-execution-lab` — 26 changeset
3. `sim-real-so101-evidence-loop` — 25 changeset

- 총 선언: ≥76 changeset 상당.
- 전환: 앞 Horizon의 닫는 기준과 최종 보고서 PASS 후 다음 Horizon을 ROADMAP current로 승격한다.
- 정지: REAL1의 실제 구매·배송·공간·카메라 구성은 별도 사용자 승인 없이는 진행하지 않는다.

## 순서 미정 후보

- **학습된 물체 상호작용 기술** — locomotion/object-contact 장면을 학습된 goal-directed skill로 확장한다.

## 근거

- `research/2026-07-20-general-next-horizon-options.md`
- `research/2026-07-20-see-understand-act-robot-lab-architecture.md`
- `research/2026-07-21-multitask-generalization-lab-policy-evaluation.md`
- `research/2026-07-21-live-instruction-execution-lab-policy-server.md`
- `research/2026-07-21-sim-real-so101-evidence-loop.md`
