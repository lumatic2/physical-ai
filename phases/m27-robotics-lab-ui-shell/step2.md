# Step 2: imagegen-favicon

## 읽어야 할 파일

- `experiments/03-digital-twin/web/index.html` - 왜: favicon link target을 확인한다.
- `experiments/03-digital-twin/web/assets/favicon.png` - 왜: 기존 asset을 덮어쓸지 versioned sibling을 둘지 판단한다.
- `docs/adr/0011-robotics-lab-v2-ui-and-environment.md` - 왜: favicon은 M27 branding asset이고 physics와 분리된다.

## 작업

`imagegen` skill의 built-in mode로 Robotics Lab favicon/app icon을 생성한다. 방향: dark lab floor grid, compact humanoid/robot silhouette, sensor glow, no text, square icon, small-size legibility. 최종 선택본은 workspace asset으로 복사하고 `index.html`이 참조하는 favicon을 교체하거나 versioned 파일로 연결한다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
node qa/favicon_check.mjs
```

## 검증 절차

1. generated image가 workspace under `assets/`에 저장됐는지 확인한다.
2. favicon link가 transient `$CODEX_HOME` path를 참조하지 않는지 확인한다.
3. Browser/Playwright에서 favicon response가 200이고 PNG dimensions가 icon으로 적합한지 확인한다.
4. 성공 시 step 2를 completed로 갱신한다.

## 금지사항

- project-referenced asset을 `$CODEX_HOME/generated_images`에만 두지 않는다.
- favicon에 텍스트를 넣지 않는다.
- 기존 asset을 덮어쓰기 전에 git diff로 확인한다.
