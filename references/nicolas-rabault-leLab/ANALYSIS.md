# nicolas-rabault/leLab 분석

> 클론: https://github.com/nicolas-rabault/leLab (`3aa1149bf102`, 2026-07-20 접근) · 라이선스 표기 없음

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

LeRobot 위에서 SO 계열 로봇의 calibration, teleoperation, joint monitoring, dataset recording, replay, training을 FastAPI로 감싼 **실물 로봇 운영 backend**다. VLM/VLA 판단 관찰기는 아니다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
leLab/
├── app/main.py          # REST·WebSocket API
├── app/recording.py     # LeRobot dataset recording
├── app/teleoperating.py # robot/leader 연결과 joint 전달
├── app/replaying.py     # dataset episode replay
├── app/training.py      # 학습 프로세스와 로그
└── scripts/             # backend와 별도 frontend 실행
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `README.md:24,33`; `app/recording.py:77-93` | 카메라 config와 joint position |
| 인지·추론 | 해당 없음 | VLM/VLA semantic observation 없음 |
| 정책·액션 생성 | `app/teleoperating.py` | leader→follower teleoperation 중심 |
| 학습·데이터 | `app/main.py:297-305`; `app/training.py` | episode recording과 training process |
| 하드웨어·배포 | `app/main.py:230-293` | arm control REST와 joint WebSocket |

## 4. 인상 깊은 코드/패턴

- `app/main.py:265-293` — joint state를 WebSocket으로 브라우저에 지속 전송하는 운영 경계가 분명하다.
- `app/main.py:297-305` — recording session을 명시적 start/stop API로 분리해 실물 데이터 수집 UX를 만든다.
- `README.md:107-110` — frontend는 `jurmy24/leLab-space`를 실행 시 별도로 clone한다. 제품이 두 저장소와 runtime 결합에 걸쳐 있어 그대로 채택할 때 재현성 비용이 있다.

## 5. 내 정의에 어떻게 반영할 것인가

- 실물 SO-101 단계의 camera/joint/recording control plane 참고로 남긴다.
- 현 Horizon은 LIBERO 시뮬레이션 evidence가 우선이라 backend를 직접 채택하지 않는다.
- 라이선스 부재, frontend 분리, VLA inference/provenance 부재 때문에 코드 복사보다 API/UX 패턴만 참고한다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 20분
- 다음 후보: jurmy24/leLab-space frontend
