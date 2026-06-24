# Step 2: grounding-physics-controls

## 읽어야 할 파일

- `experiments/33-unitree-mujoco-g1-bridge-probe/README.md` - 왜: assisted fixture, collapse rejection, unassisted controller evidence의 경계가 정의되어 있다.
- `experiments/03-digital-twin/web/src/main.js` or runtime adapter - 왜: physics stepping, replay, stream, drag force, qfrc paths가 있다.
- G1 scene XML files - 왜: floor/contact/friction/condim/contype settings baseline이다.

## 작업

Grounding/contact/physics controls를 UI에 추가한다. 예: grounding assist mode, floor friction, contact preset, solver timestep display, replay-vs-physics handoff. 첫 구현은 안전한 preset switching and summary recording을 우선하고, physical behavior change는 QA에서 observable한 범위만 허용한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=instrumented-lab --grounding=assisted
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=rough-terrain --grounding=physics
```

## 금지사항

- assisted fixture를 unassisted success로 표시하지 않는다.
- contact/friction change가 policy byte-parity claim을 깨면 해당 mode를 별도 preset으로 분리한다.
