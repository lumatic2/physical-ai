# Step 1: public-copy-refresh

## 읽어야 할 파일

- phases/m35-public-evidence-refresh/step0.md - 왜: audit 결과를 반영해야 함.
- README.md - 왜: public-facing 북극성/5분 요약 업데이트 대상.
- experiments/README.md - 왜: 실험 인덱스의 최신 Robotics Lab evidence 업데이트 대상.
- experiments/134-user-controllable-digital-twin/verify/control-smoke.json - 왜: M33 완료 evidence가 있을 때만 command evidence를 완료형으로 쓸 수 있음.
- experiments/135-mujoco-contact-force-readout/verify/contact-readout-probe.json - 왜: M34 완료 evidence가 있을 때만 physics readout claim을 쓸 수 있음.

## 작업

README와 experiments index를 M27-M34 evidence arc에 맞게 갱신하고, live `robotics.askewly.com` smoke 결과를 `experiments/136-public-evidence-refresh/verify/public-story-smoke.json`에 남긴다.

## Acceptance Criteria

```bash
cd experiments/03-digital-twin/web
npm run build
node qa/workbench_check.mjs --exp=g1-walk
```

## 검증 절차

1. README/index diff에서 claim boundary 위반 여부 확인.
2. live smoke 가능 시 URL과 결과를 evidence artifact에 저장.
3. ROADMAP M35 DoD 충족 시 `roadmap_sync.py complete --milestone M35 --evidence experiments/136-public-evidence-refresh/verify/public-story-smoke.json --summary "<한 줄 결과>"`.

## 금지사항

- `robotics.askewly.com`의 live 상태를 확인하지 않고 live claim을 강화하지 마라.
- 실물 bring-up 대기 항목을 완료처럼 쓰지 마라.
