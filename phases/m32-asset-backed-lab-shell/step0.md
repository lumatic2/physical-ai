# Step 0: lab-shell-asset-contract

## 읽어야 할 파일

- `DESIGN.md` - 왜: asset shell이 따라야 할 lab visual direction을 확인한다.
- `docs/ARCHITECTURE.md` - 왜: asset scene layer와 lazy-load/performance guardrail이 정의되어 있다.
- `experiments/03-digital-twin/web/src/main.js` - 왜: Lab Visual Layer에 asset을 붙일 위치를 확인한다.

## 작업

lightweight glTF lab shell asset을 `experiments/03-digital-twin/web/assets/lab/`에 만들고, manifest/metadata를 함께 둔다. asset은 public visual layer용이며 collision 또는 physics claim을 만들지 않는다.

## Acceptance Criteria

```bash
node -e "const m=require('./experiments/03-digital-twin/web/assets/lab/lab_shell_manifest.json'); if(!m.pass) process.exit(1)"
```

## 금지사항

- 외부 CDN asset에 의존하지 마라.
- asset을 MuJoCo collision으로 쓰지 마라.
