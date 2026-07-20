# jurmy24/leLab-space 분석

> 클론: https://github.com/jurmy24/leLab-space (`b37933caa5cb`, 2026-07-20 접근) · 라이선스 표기 없음 · Git LFS quota 초과로 clean checkout 불가

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

LeLab backend를 위한 React UI로 camera 설정, URDF, episode 목록, playback control, training log 화면을 제공하는 **실물 로봇 운영 UI shell**이다. replay camera와 episode data 연결은 아직 placeholder 성격이 강하다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
leLab-space/
├── src/components/recording/ # camera detection·preview·record config
├── src/components/replay/    # episode selector·control·URDF shell
├── src/components/control/   # robot command와 visualizer
├── src/components/training/  # config, monitoring, logs
└── public/so-101-urdf/       # SO-101 geometry
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `CameraConfiguration.tsx:98-175` | browser camera 탐색·preview |
| 인지·추론 | 해당 없음 | command UI는 있으나 VLM/VLA trace 없음 |
| 정책·액션 생성 | `components/control/` | teleoperation/control UI |
| 학습·데이터 | `TrainingLogs.tsx:28-37`; `components/replay/` | 학습 로그와 episode 선택 shell |
| 하드웨어·배포 | `ReplayVisualizer.tsx:17-34`; `public/so-101-urdf/` | 브라우저 URDF viewer |

## 4. 인상 깊은 코드/패턴

- `src/components/recording/CameraConfiguration.tsx:98-137,149-175` — backend camera 목록과 browser `MediaDevices` fallback을 함께 쓰고 실제 device id로 preview를 고정한다.
- `src/components/replay/ReplayVisualizer.tsx:17-34` — URDF 중심 화면 아래 4개 camera feed 자리를 설계했지만 현재 `VideoOff`와 label만 렌더링한다.
- `src/components/replay/EpisodePlayer.tsx:28-68` — episode 선택과 시간 control UI는 있으나 camera/state/action payload 연결은 없다.
- `src/components/training/monitoring/TrainingLogs.tsx:28-37` — training process log용이고 로봇 판단 로그가 아니다.

## 5. 내 정의에 어떻게 반영할 것인가

- “로봇 운영실” 정보 구조와 camera setup UX는 좋은 참고다.
- 완성 시스템으로 채택하지 않는다. 사용자가 원하는 dual-camera episode와 판단/action timeline의 핵심 부분이 placeholder다.
- 라이선스 부재와 Git LFS quota 초과도 fork 기반 의존성에 불리하다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 20분
- 다음 후보: 공식 LeRobot Dataset Visualizer
