# 147 — Camera-to-Action Episode Contract

LAB1은 LIBERO rollout의 main/wrist camera, state, language instruction, executed action, outcome을 같은 재생 가능한 episode로 보존한다.

## 현재 상태

- 공식 viewer 재사용 probe 완료: [결과와 evidence](verify/official-viewer-reuse/README.md).
- 결론: LeRobot v3 episode를 canonical format으로, Rerun을 내부 replay 기준선으로 사용한다.
- 승인된 실행안: [LAB1 LeRobot episode 증거](../../plans/2026-07-21-lab1-lerobot-episode-evidence.md).
- canonical profile: `episode_profile.py`가 LeRobot metadata와 선택적 LAB provenance sidecar를 검증한다.

## Profile 명령

```powershell
python test_episode_profile.py
python episode_profile.py --info fixtures/lerobot-libero-info.json
python episode_profile.py --info fixtures/lerobot-libero-info.json --provenance fixtures/valid-provenance.json --require-provenance
```

LeRobot episode는 camera/state/action/timestamp/task mapping의 정본이다. sidecar는 pinned revision, camera role, latency, outcome과 claim boundary만 소유하며 canonical field를 복제하면 validator가 거부한다.

## Probe 명령

```powershell
python test_probe_official_viewers.py
python probe_official_viewers.py --dataset-root <root> --rrd <episode.rrd> --output <report.json>
python probe_foxglove_channels.py --output <report.json>
```

공개 dataset replay는 local VLA inference 성공 증거가 아니다. 실제 producer evidence는 addendum 승인 후 bounded LIBERO rollout에서 생성한다.
