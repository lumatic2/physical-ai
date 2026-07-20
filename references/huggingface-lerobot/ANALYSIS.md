# huggingface/lerobot 분석 — 관찰 경로 갱신

> 클론: https://github.com/huggingface/lerobot (`ddc2aa7a27ba`, 2026-07-20 접근) · 라이선스: Apache-2.0

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

로봇 인터페이스·데이터셋·정책 학습·추론을 통합하면서, 현재는 Rerun 실시간 control-loop 시각화와 Foxglove 탐색형 episode replay까지 직접 제공하는 **로봇 학습 실행 하네스**다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
lerobot/
├── src/lerobot/robots/       # 실물 로봇 interface
├── src/lerobot/policies/     # ACT, SmolVLA 등 정책
├── src/lerobot/datasets/     # Parquet+video episode format
├── src/lerobot/scripts/      # record, train, dataset visualization CLI
└── src/lerobot/utils/        # Rerun·Foxglove 관찰 backend
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `utils/rerun_visualization.py:121-126,153-173` | camera image와 scalar state를 type별로 기록 |
| 인지·추론 | `src/lerobot/policies/` | VLA·imitation policy 구현과 inference |
| 정책·액션 생성 | `utils/rerun_visualization.py:176-188` | action scalar/array를 별도 entity로 기록 |
| 학습·데이터 | `scripts/lerobot_dataset_viz.py:252-286` | dataset timestep에 image/state/action/reward/success 동기화 |
| 하드웨어·배포 | `utils/foxglove_visualization.py:408-512` | live/control 및 seekable dataset WebSocket playback |

## 4. 인상 깊은 코드/패턴

- `scripts/lerobot_dataset_viz.py:134-151` — camera image와 action/state/reward/done/success를 고정 Blueprint 한 화면에 배치한다.
- `utils/rerun_visualization.py:76-90` — 실제 control loop에서도 camera는 `Spatial2DView`, state/action은 `TimeSeriesView`로 자동 구성한다.
- `scripts/lerobot_dataset_viz.py:62-72,402-406` — 같은 episode를 Foxglove의 play/pause/scrub 가능한 WebSocket source로 제공한다.
- `utils/foxglove_visualization.py:466-512` — image, state, action, reward, done, success를 dataset 시간으로 재전송한다.

## 5. 내 정의에 어떻게 반영할 것인가

- LAB1은 독자 viewer/schema부터 만들지 말고 LeRobot episode와 공식 `lerobot-dataset-viz`를 기준선으로 probe한다.
- Rerun은 live/internal debugging, Foxglove는 메시지 중심 진단의 비교군으로 둔다. 둘 다 공식 adapter가 있으므로 첫 changeset은 “작동 확인과 gap 측정”이어야 한다.
- 프로젝트 고유 추가분은 instruction, model revision, latency, `sensor|vlm|vla|controller|environment` provenance와 PASS/FAIL raw link다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 35분
- 다음 후보: 공식 LeRobot Dataset Tool and Visualizer
