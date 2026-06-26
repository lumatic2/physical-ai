# Step 0: claim-audit

## 읽어야 할 파일

- README.md - 왜: public 5분 story의 중심 문서.
- experiments/README.md - 왜: experiment index의 milestone summary가 public evidence map 역할을 함.
- ROADMAP.md - 왜: M27-M35 current evidence boundary를 확인해야 함.
- docs/PRD.md - 왜: 성공 기준과 제외 범위 확인.
- docs/adr/0012-controllable-physics-evidence-workbench.md - 왜: contact/control evidence claim 경계 확인.

## 작업

README와 experiment index에서 M27-M34 evidence가 빠졌거나, real robot telemetry/unassisted controller/physics readout을 과장할 위험이 있는 문장을 목록화한다. 수정 전 audit artifact를 만든다.

## Acceptance Criteria

```bash
git diff -- README.md experiments/README.md docs/PRD.md docs/ARCHITECTURE.md
```

## 검증 절차

1. stale claim과 missing evidence 목록을 `experiments/136-public-evidence-refresh/verify/claim-audit.md`에 저장.
2. 수정 후보가 M33/M34 evidence 상태와 모순되지 않는지 확인.
3. `phases/m35-public-evidence-refresh/index.json` step 0 상태 갱신.

## 금지사항

- evidence가 없는 미래형 claim을 README에 먼저 쓰지 마라. 이유: M35는 packaging이 아니라 evidence story refresh다.
- M33/M34가 완료되지 않았다면 완료형 문장으로 쓰지 마라.
