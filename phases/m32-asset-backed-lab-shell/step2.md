# Step 2: asset-shell-evidence

## 읽어야 할 파일

- `experiments/03-digital-twin/web/qa/asset_shell_check.mjs` - 왜: M32 통합 smoke 생성에 사용한다.
- `experiments/03-digital-twin/web/assets/lab/lab_shell_manifest.json` - 왜: asset budget과 path를 evidence에 기록한다.

## 작업

M32 README와 `verify/asset-lab-shell-smoke.json`을 작성한다. build, asset check, visual QA screenshot path, bundle size budget을 기록한다.

## Acceptance Criteria

```bash
node -e "const e=require('./experiments/133-asset-backed-lab-shell/verify/asset-lab-shell-smoke.json'); if(!e.pass) process.exit(1)"
```

## 금지사항

- asset-backed를 photorealistic이라고 주장하지 마라. lightweight shell evidence로 제한한다.
