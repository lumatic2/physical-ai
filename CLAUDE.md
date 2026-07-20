# physical-ai

> 카메라·센서·언어 지시가 로봇 행동으로 변환되는 과정을 실행·관찰·검증하는 피지컬 AI 실험실. (갈래: learning + product)

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
