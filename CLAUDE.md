# physical-ai

> 카메라·센서·언어 지시가 로봇 행동으로 변환되는 과정을 실행·관찰·검증하는 피지컬 AI 실험실. (갈래: learning + product)

## 북극성 — 사용자 소유, 승인 없이 수정 금지

> 이 절은 **사용자 소유**다. 에이전트는 문구 후보를 제안하고, 대화에서 확정 문구를 되읽어 **명시 승인을 받은 뒤에만** 그대로 기록한다. 승인 전 자율 수정 금지. 갱신은 **방향 자체가 바뀔 때만** — Milestone 완료는 여기를 바꾸지 않는다.
> 2026-07-23 하네스 재조립(C4)으로 구 OBJECTIVE 문서를 이 절로 흡수했다. 계획 계층이 Objective→Horizon→Milestone→Step 4단에서 **2계층**(이 문서 = 방향+규칙 / 작업 단위 계획서)으로 줄었다.

### 북극성

피지컬 AI를 문헌·코드 이해에서 끝내지 않고, 컨슈머 하드웨어에서 정책을 직접 실행·학습·비교하며, 시뮬레이션부터 실물까지 동일한 증거 계약으로 검증 가능한 포트폴리오를 만든다.

### 성공 모습

- 카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실.
- 제3자가 문헌과 코드에서 출발한 정책 실행·학습·비교 결과를 재현 가능한 산출물로 확인할 수 있다.
- 시뮬레이션과 실물 로봇의 주장을 같은 증거 계약으로 구분해, 검증된 능력과 아직 검증되지 않은 한계가 함께 드러난다.

### 움직이는 축

- **이해에서 실증으로**: 문헌·코드 이해를 직접 실행, 수치 비교, 재현 가능한 실험 증거로 끌어올린다.
- **데모에서 실험 플랫폼으로**: 관전형 결과물을 조작·측정·검증 가능한 정책 및 디지털 트윈 플랫폼으로 끌어올린다.
- **시뮬레이션에서 실물로**: 시뮬레이션 증거를 실물 telemetry와 안전 게이트로 이어지는 검증 체계로 확장한다.

### 긴 arc

- 피지컬 AI 문헌과 구현을 정독하고, 동작 표현과 정책 구조를 비교한다.
- 컨슈머 하드웨어에서 정책을 직접 실행·학습하고 동일한 기준으로 실측한다.
- 학습 정책을 브라우저 디지털 트윈에서 조작·측정·검증 가능한 형태로 공개한다.
- 동일한 증거 계약을 실물 로봇의 telemetry와 안전 게이트까지 연결한다.

## 기술 스택
- Current public twin: MuJoCo WASM + Three.js + vanilla ES modules under `experiments/03-digital-twin/web`.
- Planned Robotics Lab v2 shell: Vite + React + Tailwind CSS + shadcn/ui, while preserving the existing MuJoCo canvas/runtime and QA contracts.
- Observable arm lab producer: Python/WSL2 + LIBERO/robosuite/MuJoCo + LeRobot-compatible VLM/VLA policies; canonical episodes are exported as versioned traces for deterministic browser replay.
- Visual asset workflow: project-bound raster favicon/app icon assets are generated with the `imagegen` skill, then saved under `experiments/03-digital-twin/web/assets/`.

## 프로젝트 구조
-

## 개발 명령어
```bash
# Current static MuJoCo viewer
cd experiments/03-digital-twin/web
python serve_coi.py 8132
node qa/visual_check.mjs --exp=unitree-g1-elastic-stand --steps=1 --chunk=1
node qa/workbench_check.mjs --exp=unitree-g1-elastic-stand
```

## 작업 방식
- 레포 분석은 "전체 다 읽기" X, `references/ANALYSIS_TEMPLATE.md` 의 5섹션 채우기 O
- 시간 박스: 레포당 90분
- 외부 정의 5개 이상 모이기 전 자기 정의 확정 금지

## ⚠ Judge 규약
> 새 reference 분석은 5섹션을 다 채우기 전에 정의 갱신·통찰 보고 금지. 인용은 출처 + 접근일 필수.

## 의사결정 이력
"왜 X 안 함?" 같은 *의도적으로 안 한 선택*은 `docs/adr/` 에 ADR 로 보존.
