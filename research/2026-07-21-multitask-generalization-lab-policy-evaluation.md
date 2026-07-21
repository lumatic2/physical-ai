# 여러 과제 정책 평가 Horizon 조사

- 조사일: 2026-07-21
- 소비처: `multitask-generalization-lab`
- 질문: 단일 LIBERO 과제의 공개 증거를 여러 과제·정책의 공정한 비교 제품으로 확장할 때 무엇을 재사용하고 무엇을 새로 만들어야 하는가?

## 현재 간극

LAB1~LAB3는 LIBERO의 한 과제에서 OpenVLA PASS/FAIL, 별도 Qwen3-VL→scripted skill lane과 공개 episode drill-down을 검증했다. 남은 간극은 같은 깊이의 증거를 사전 고정한 여러 과제와 두 정책에 적용해 cherry-pick이 아닌 aggregate 결과를 만드는 것이다. 기존 episode/provenance/public replay 계약은 재사용 가능하고, 새로 필요한 것은 task matrix, policy compatibility, resumable evaluation, paired statistics와 실패 양상 계약이다.

## 외부 근거

- LIBERO는 Spatial, Object, Goal, LIBERO-100의 130개 과제와 고정 초기 상태를 제공한다. 첫 Horizon은 전체 130개가 아니라 controlled distribution shift를 가진 앞의 세 suite에서 4개씩 뽑아 평가 계약을 먼저 검증하는 것이 맞다. 출처: https://github.com/Lifelong-Robot-Learning/LIBERO (접근일: 2026-07-21)
- OpenVLA는 LIBERO 평가와 LoRA/full fine-tuning 경로를 제공하고, OFT는 다중 이미지와 더 빠른 inference를 지원한다고 안내한다. 기존 OpenVLA lane의 계약과 failure evidence를 유지하는 기준선으로 적합하다. 출처: https://github.com/openvla/openvla (접근일: 2026-07-21)
- openpi는 π₀.₅-LIBERO checkpoint, LeRobot 데이터 변환, policy server와 LIBERO evaluation 경로를 제공한다. 다른 policy family를 같은 observation/action adapter에 연결하는 비교 후보로 적합하다. 출처: https://github.com/Physical-Intelligence/openpi (접근일: 2026-07-21)
- LeRobot는 대규모 episode를 Parquet+video 계약으로 저장·stream·visualize하고 여러 policy 및 simulation/real evaluation을 한 도구군에서 다룬다. 기존 LAB episode 정본을 버리지 않고 multi-task index를 얹는 근거다. 출처: https://github.com/huggingface/lerobot (접근일: 2026-07-21)
- LeRobot agent guide는 안정적인 성공률 평가에 50회 이상 episode와 baseline 비교를 권한다. 12개 task×5 initial state=60 episode/policy는 최소 표본 하한과 task coverage를 동시에 충족하는 현실적 slice다. 출처: https://github.com/huggingface/lerobot/blob/main/AGENT_GUIDE.md (접근일: 2026-07-21)

## 채택 결정

1. 평가군은 LIBERO Spatial/Object/Goal에서 각 4개 task, task마다 고정 initial state 5개로 사전 선언한다.
2. 정책은 현재 OpenVLA 기준선과 π₀.₅-LIBERO를 exact revision으로 비교한다. policy별 suite checkpoint 차이는 compatibility registry에 공개하며 하나의 범용 checkpoint처럼 표현하지 않는다.
3. 각 정책은 60 episode를 실행하고 success, termination, steps, latency와 canonical evidence hash를 보존한다.
4. 실패는 추정 원인이 아니라 관측 가능한 양상만 분류하고 증거가 부족하면 `unknown`으로 남긴다.
5. 공개 UI는 aggregate matrix에서 기존 LAB3 episode drill-down으로 내려가는 얇은 index layer로 제한한다.

## 제외

- LIBERO 130개 전체 실행: 첫 평가 계약을 검증하기 전에 compute와 artifact가 과도하게 커진다.
- 새 foundation model 학습: 비교 계약보다 학습 인프라가 Horizon을 지배한다.
- 실시간 public GPU backend: 공개 재현성과 비용 경계를 흐린다.
- 단일 성공률 순위표: task/suite denominator와 failure evidence를 숨겨 비교를 왜곡한다.

## 조사 종료 판단

LIBERO, OpenVLA, openpi, LeRobot와 평가 지침을 대조한 뒤 추가 소스는 task 수·adapter 세부만 보강했고 새로운 시스템 부류를 추가하지 않았다. 환경, 두 policy family, episode 정본, 공개 viewer의 네 층으로 후보가 포화되어 조사를 종료한다.
