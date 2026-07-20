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

## LIBERO writer

`libero_writer.py`는 [LeRobotDataset current source](https://github.com/huggingface/lerobot/blob/main/src/lerobot/datasets/lerobot_dataset.py)의 `create → add_frame → save_episode → finalize` 흐름과 [multi-camera feature contract](https://github.com/huggingface/lerobot/blob/main/src/lerobot/utils/feature_utils.py)를 사용한다(접근일 2026-07-21).

```powershell
python test_libero_writer.py
python mock_writer_smoke.py --root <empty-dataset-root> --output <report.json>
```

실제 client recording은 `--record-root`와 pinned `--dataset-revision`, `--environment-revision`, `--policy-revision` 세 값을 모두 요구한다. record flag가 없으면 기존 평가 동작을 유지한다. current OpenVLA checkpoint는 main camera만 소비하므로 wrist camera는 저장하되 provenance에 `model_input=false`로 기록한다.

## Bounded Rerun evidence

`verify_bounded_evidence.py`는 canonical dataset tree, sidecar와 RRD를 SHA-256으로 묶고 official `rerun rrd verify/stats`에서 두 camera, state, action과 frame/timestamp timeline을 확인한다. `producer_kind=synthetic-smoke`는 writer/viewer 호환 증거일 뿐 OpenVLA 실행 증거가 아니며, 실제 rollout만 `producer_claim_ready=true`가 될 수 있다.

```powershell
python test_verify_bounded_evidence.py
python verify_bounded_evidence.py --dataset-root <root> --sidecar <sidecar.json> --rrd <episode.rrd> --rerun-cli <rerun.exe> --expected-frames <n> --producer-kind openvla-libero --output <report.json>
```

## Probe 명령

```powershell
python test_probe_official_viewers.py
python probe_official_viewers.py --dataset-root <root> --rrd <episode.rrd> --output <report.json>
python probe_foxglove_channels.py --output <report.json>
```

공개 dataset replay는 local VLA inference 성공 증거가 아니다. 실제 producer evidence는 [bounded OpenVLA + LIBERO evidence](verify/bounded-smoke/README.md)에 별도로 고정돼 있다.
