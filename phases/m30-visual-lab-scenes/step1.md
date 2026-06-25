# Step 1: visual-scene-evidence

## 읽어야 할 파일

- `phases/m30-visual-lab-scenes/index.json` - 왜: Step 0 summary를 이어받아 evidence를 작성한다.
- `experiments/03-digital-twin/web/qa/environment_check.mjs` - 왜: preset summary를 증거 JSON으로 수집할 때 재사용한다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: QA summary의 visualLayer object list를 확인한다.

## 작업

M30 증거 폴더를 만들고 preset별 environment summary, rendered smoke 결과, README, 통합 verify JSON을 남긴다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-walk
```

추가로 `experiments/131-visual-lab-scenes/verify/visual-lab-scenes-smoke.json`의 `pass`가 `true`여야 한다.

## 검증 절차

1. preset별 QA summary를 수집한다.
2. visual-only contract와 preset별 object diversity를 통합 JSON에 기록한다.
3. `phases/m30-visual-lab-scenes/index.json` step 업데이트.

## 금지사항

- M31 physical terrain claim을 evidence에 섞지 마라.
- screenshot/report를 repo 외부 temp에만 두고, committed evidence는 JSON/README 중심으로 둔다.
