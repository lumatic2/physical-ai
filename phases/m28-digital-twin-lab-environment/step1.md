# Step 1: laboratory-scene-visuals

## 읽어야 할 파일

- `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_policy.xml` - 왜: current floor, skybox, lights baseline이다.
- `experiments/03-digital-twin/web/assets/scenes/g1/scene_g1_rough.xml` - 왜: terrain/contact baseline이다.
- `experiments/03-digital-twin/web/src/main.js` or `TwinViewport` adapter - 왜: Three.js background/fog/lights and camera framing are applied here.

## 작업

Robot inspection lab feel을 만든다. 우선 Three.js environment/background/floor material과 MuJoCo XML scene variants를 조심스럽게 분리한다. 실험실 배경은 visual layer에서 시작하고, contact-bearing geometry는 별도 scene/preset으로만 추가한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/environment_check.mjs --exp=unitree-g1-elastic-stand --preset=instrumented-lab
node qa/visual_check.mjs --exp=unitree-g1-elastic-stand --steps=1 --chunk=1
```

## 금지사항

- 배경 장식 geometry가 robot contact를 의도치 않게 바꾸지 않게 한다.
- camera framing을 깨뜨려 robot이 잘리지 않게 한다.
