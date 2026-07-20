# rerun-io/rerun 분석

> 클론: https://github.com/rerun-io/rerun (`507732f7e299`, 2026-07-20 접근) · 라이선스: Apache-2.0

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

로봇·시뮬레이터의 이미지, 3D, 관절 상태, 시계열, 텍스트를 같은 시간축에 기록하고 실시간 또는 episode replay로 보는 **멀티모달 관찰 하네스**다. 정책을 실행하지는 않지만 이번 실험실의 내부 증거 뷰어에 가장 가깝다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
rerun/
├── rerun_py/       # Python logging SDK와 archetype
├── crates/         # 저장소, viewer, web viewer의 Rust 구현
├── docs/           # Blueprint·web serving·query 문서
└── examples/       # 로보틱스·비전·LeRobot 예제
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `README.md:20,35` | image, point cloud, transform, joint state, video 등 다중 rate 입력 |
| 인지·추론 | 해당 없음 | 모델 추론기는 아니며 모델 내부 표현을 받아 표시 |
| 정책·액션 생성 | 해당 없음 | action 시계열도 일반 데이터로 기록 |
| 학습·데이터 | `README.md:20` | MCAP, RRD, LeRobot 입력과 columnar storage/query |
| 하드웨어·배포 | `docs/snippets/all/howto/serve_web_viewer.py:7-12` | Python SDK에서 gRPC와 web viewer를 함께 구동 |

## 4. 인상 깊은 코드/패턴

- `README.md:20` — 여러 카메라·상태·action을 동기화하고 episode를 scrub하는 기능이 제품의 LAB1 관찰 계약과 이미 겹친다.
- `docs/content/howto/visualization/build-a-blueprint-programmatically.md:6-10,215-218` — 화면 배치를 코드로 고정하고 `TextDocumentView`와 `TimeSeriesView`를 함께 놓을 수 있어 재현 가능한 실험실 layout을 만들 수 있다.
- `docs/snippets/all/howto/serve_web_viewer.py:7-12` — 별도 데스크톱 앱 없이 browser viewer로 연결할 수 있다.

## 5. 내 정의에 어떻게 반영할 것인가

- LAB1의 내부 증거 뷰어와 trace probe는 Rerun을 우선 사용한다. 이미지·state·action 타임라인을 새로 구현하지 않는다.
- Rerun의 generic entity tree를 공개 설명 UX로 그대로 쓰지는 않는다. 공개 화면은 source-tagged VLM/VLA/controller 의미를 얇은 제품 UI로 설명한다.
- `.rrd`는 검증·디버깅 산출물 후보이고, 장기 정본은 LeRobot episode와 프로젝트 provenance manifest를 분리 검토한다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 25분
- 다음 후보: Hugging Face LeRobot의 Rerun/Foxglove backend
