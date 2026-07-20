# LAB1 공식 viewer 재사용 probe 결과

> 실행일: 2026-07-21 · 공개 데이터만 사용 · recorded episode 재생은 이 레포의 live VLA 실행 증거가 아니다.

## 결론

**LeRobot episode를 정본으로 채택하고, 공개 실험실 UI는 LeRobot Dataset Visualizer의 검증된 상호작용을 이식한다. Rerun은 내부 분석 화면으로 그대로 쓰고, Foxglove는 선택형 채널 진단 도구로 둔다.** 세 도구를 하나의 공개 제품으로 통째로 합치거나 fork할 필요는 없다.

| 후보 | 실제 결과 | 판정 | 가져올 것 |
|---|---|---|---|
| LeRobot v3 episode | dual camera + state + action + instruction이 실제 sample에서 함께 존재 | **채택** | LAB1 저장 계약 |
| Rerun | 37.1MB RRD 생성·검증, 2 camera + action/state + scrub 한 화면 PASS | **그대로 사용** | 내부 replay/debug viewer |
| Foxglove SDK server | 4 required channel + `playbackControl` + `time` 광고 PASS | **선택형 사용** | 메시지/channel 진단과 seek 비교군 |
| Foxglove Web | 로그인 화면으로 redirect | **공개 UI에는 제외** | 링크 또는 개발자용 안내만 |
| LeRobot Dataset Visualizer | 배포본은 2 video + instruction + graph + scrub PASS | **상호작용·컴포넌트 이식** | 공개 episode 화면의 기준 디자인 |
| Visualizer 전체 app vendoring | 현재 source local run에서 Recharts runtime error | **fork/통째 의존은 보류** | 필요한 component와 data contract만 좁게 이식 |

## 확인한 episode 계약

- 공개 source: [`lerobot/libero`](https://huggingface.co/datasets/lerobot/libero) (접근일 2026-07-21).
- episode 0: 214 frames, 10fps, 21.3s.
- main camera `observation.images.image`: float32 CHW `[3, 256, 256]`.
- wrist camera `observation.images.image2`: float32 CHW `[3, 256, 256]`.
- state `[8]`, action `[7]`, timestamp, task instruction 존재.
- machine-readable evidence: [dataset-contract.json](./dataset-contract.json).

## 현재 LIBERO evaluator와의 최소 adapter 경계

새 adapter는 정책 서버나 simulator를 다시 쓰지 않는다. 기존 [`client.py`](../../../01-vla-local-eval/client.py)의 rollout loop에서 **관측을 읽은 직후부터 `env.step()` 직전**만 감싼다.

| 현재 값 | LeRobot feature | 필요한 처리 |
|---|---|---|
| `obs["agentview_image"]` | `observation.images.image` | uint8 HWC 원본을 main camera로 저장 |
| eye-in-hand observation | `observation.images.image2` | env observation key를 1회 확인하고 wrist camera로 저장; 없으면 episode 생성 거부 |
| `robot0_eef_pos + axis-angle(eef_quat) + robot0_gripper_qpos` | `observation.state` | 기존 legacy evaluator와 같은 8-dim 집계 복원 |
| `task.language` | `task` | episode instruction으로 저장 |
| normalize + invert 후 action | `action` | simulator에 실제 전달한 7-dim action 저장 |
| loop frame index / fps | `timestamp` | 10fps 기준 source timestamp 저장 |
| raw policy action·latency·model revision·success | LAB2 provenance sidecar | canonical action과 섞지 않고 별도 event로 저장 |

따라서 구현 지점은 `client.py:85-95` 한 군데다. `add_frame(observation, action, task)`를 `env.step()` 바로 앞에 넣고, trial 종료 시 `save_episode()`와 결과 sidecar를 닫으면 된다. 현재 modern client는 main camera와 실행 action만 남기므로 wrist/state/latency/provenance를 추가해야 한다.

## UI 재사용 범위

공식 배포 화면인 [LeRobot Dataset Visualizer](https://huggingface.co/spaces/lerobot/visualize_dataset?path=%2Flerobot%2Flibero%2Fepisode_0) (접근일 2026-07-21)에서 다음을 실제 브라우저로 확인했다.

- 2개 camera video가 같은 episode clock을 사용한다.
- language instruction이 영상 바로 아래에 고정된다.
- observation/action graph의 cursor가 video seek와 함께 움직인다.
- play/pause, ±5s, rewind, slider, episode navigation이 이미 있다.
- screenshot: [lerobot-dataset-visualizer.png](./lerobot-dataset-visualizer.png).

우리 공개 화면에는 `simple-videos-player`, 공통 playback bar, synchronized Recharts 패턴을 선택적으로 이식한다. 대신 dataset cleaning용 1,693-episode sidebar·Filtering·Doctor는 제외하고, 오른쪽에 `관측 → 모델 판단 → 실행 action → 결과` provenance lane을 새로 둔다. 공식 repo는 Apache-2.0인 [GitHub source](https://github.com/huggingface/lerobot-dataset-visualizer)를 기준으로 한다(접근일 2026-07-21).

## Rerun과 Foxglove

LeRobot 공식 CLI source는 [huggingface/lerobot](https://github.com/huggingface/lerobot)이다(접근일 2026-07-21).

- Rerun RRD는 `rrd verify` PASS, 5 entity paths, 857 rows, 4 sorted timelines였다. 화면은 [rerun-viewer.png](./rerun-viewer.png).
- Foxglove server는 `/observation/images/image`, `/observation/images/image2`, `/observation/state`, `/action/state`와 seek/time capability를 광고했다. raw evidence는 [foxglove-channels.json](./foxglove-channels.json).
- Foxglove 공식 deep-link 규약은 WebSocket source를 지원하지만, 실제 Web UI는 sign-in을 요구했다. [Foxglove shareable links 문서](https://docs.foxglove.dev/docs/visualization/shareable-links) (접근일 2026-07-21).

## 실패·운영 마찰

1. `torchcodec`가 설치된 Windows에서는 공유 FFmpeg DLL을 읽지 못해 공식 Rerun export가 처음 실패했다. 격리 환경에서 `torchcodec`를 제거하자 공식 PyAV fallback으로 PASS했다. LAB adapter는 이 머신에서 `video_backend="pyav"`를 명시한다.
2. Dataset Visualizer의 배포본은 PASS했지만 같은 source의 local dev run은 Recharts tooltip에서 runtime error가 났다. 그러므로 전체 app을 vendoring하지 않고, 필요한 component contract를 현재 public Vite/React 앱에 이식한다.
3. Foxglove의 현재 SDK subprotocol은 `foxglove.sdk.v1`이며 과거 `foxglove.websocket.v1`로 접속하면 HTTP 400이다. probe는 서버가 광고하는 현재 계약을 직접 검사한다.

## 다음 계획에 반영할 결정

1. LAB1: 기존 evaluator를 LeRobot writer로 감싸 dual-camera episode 하나를 실제 생성한다.
2. LAB2: 모델 raw output·latency·revision·success를 episode와 같은 clock의 provenance sidecar로 정의한다.
3. LAB3: Dataset Visualizer의 video/playback/chart interaction을 현재 공개 앱에 이식하고 provenance lane만 새로 만든다.
4. Rerun은 즉시 개발자 replay 기준선으로 사용하고, Foxglove UI 통합은 하지 않는다.

## 재현

```powershell
python experiments/147-camera-action-episode-contract/test_probe_official_viewers.py
python experiments/147-camera-action-episode-contract/probe_official_viewers.py --dataset-root <root> --rrd <episode.rrd> --output <report.json>
python experiments/147-camera-action-episode-contract/probe_foxglove_channels.py --output <report.json>
```
