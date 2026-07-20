# 147 — Camera-to-Action Episode Contract

LAB1은 LIBERO rollout의 main/wrist camera, state, language instruction, executed action, outcome을 같은 재생 가능한 episode로 보존한다.

## 현재 상태

- 공식 viewer 재사용 probe 완료: [결과와 evidence](verify/official-viewer-reuse/README.md).
- 결론: LeRobot v3 episode를 canonical format으로, Rerun을 내부 replay 기준선으로 사용한다.
- 후속 실행안: [LAB1 재사용 addendum](../../plans/2026-07-21-lab1-official-viewer-reuse-addendum.md) — 사용자 승인 대기.

## Probe 명령

```powershell
python test_probe_official_viewers.py
python probe_official_viewers.py --dataset-root <root> --rrd <episode.rrd> --output <report.json>
python probe_foxglove_channels.py --output <report.json>
```

공개 dataset replay는 local VLA inference 성공 증거가 아니다. 실제 producer evidence는 addendum 승인 후 bounded LIBERO rollout에서 생성한다.
