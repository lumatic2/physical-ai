# huggingface/lerobot-dataset-visualizer 분석

> 클론: https://github.com/huggingface/lerobot-dataset-visualizer (`5bae289b5336`, 2026-07-20 접근) · 라이선스: Apache-2.0

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

LeRobot episode의 복수 camera video, sensor/action graph, 언어 annotation, URDF를 브라우저에서 동기 재생하는 **로봇 데이터 검사 웹앱**으로, 공개 실험실 UI와 가장 가까운 오픈소스 화면이다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
lerobot-dataset-visualizer/
├── src/app/[org]/[dataset]/[episode]/  # episode fetch와 화면 조합
├── src/components/                     # video, chart, timeline, URDF, annotation
├── src/types/                          # dataset·language·video 계약
└── backend/                            # annotation parquet rewrite와 Hub push
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `README.md:18,34-35` | 복수 video와 sensor telemetry 동기화 |
| 인지·추론 | `README.md:40,111-112` | VQA·plan·memory 등 annotation 표시/편집, 실제 inference는 없음 |
| 정책·액션 생성 | `README.md:37` | action/state 정렬과 품질 분석, 정책 실행은 없음 |
| 학습·데이터 | `backend/app.py`, `README.md:109-138` | LeRobot v3.1 parquet 언어 column 편집 |
| 하드웨어·배포 | `package.json` | Next.js 15 + React 19 웹앱, URDF는 Three.js 사용 |

## 4. 인상 깊은 코드/패턴

- `src/app/[org]/[dataset]/[episode]/episode-viewer.tsx:698-732` — 복수 video, Language Instruction, interactive chart, 공통 PlaybackBar가 이미 한 화면에 조합된다.
- `src/components/simple-videos-player.tsx:281-305,346` — 모든 camera video를 공통 `currentTime`으로 seek하고 동적으로 렌더링한다.
- `src/app/[org]/[dataset]/[episode]/episode-viewer.tsx:746-768` — video 위 annotation 작업과 annotation timeline이 같은 재생축을 공유한다.
- `README.md:40` — subtask/plan/memory/VQA를 명시적 language atom으로 저장하므로 “가짜 생각 로그” 대신 출처 있는 semantic event를 설계하는 참고가 된다.

## 5. 내 정의에 어떻게 반영할 것인가

- LAB3에서 dual-camera 동기화, scrub, chart, language instruction을 처음부터 발명하지 않는다. 이 저장소를 fork하기보다 component/data contract를 먼저 probe한다.
- dataset cleaning 중심 정보 구조를 그대로 복제하지 않고 reviewer용 `관측→판단→행동→결과` 서사와 provenance lane만 추가한다.
- VQA/plan annotation은 모델 실행 로그가 아니다. 생성 주체·모델·시점을 검증한 경우에만 LAB2 event로 승격한다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 30분
- 다음 후보: LeLab의 실제 로봇 운영 UI
