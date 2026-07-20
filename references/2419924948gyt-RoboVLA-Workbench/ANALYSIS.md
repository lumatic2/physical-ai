# 2419924948gyt/RoboVLA-Workbench 분석

> 클론: https://github.com/2419924948gyt/RoboVLA-Workbench (`14dcdc7ccc74`, 2026-07-20 접근) · 라이선스 표기 없음 · 2026-06-07 단일 commit

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

자연어와 scene JSON을 symbolic action sequence로 바꾸고 Matplotlib 2D frame을 Gradio gallery에 내보내는 **VLA 모양의 교육용 prototype**이다. 물리 simulator나 연속 robot action은 없다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
RoboVLA-Workbench/
├── app.py                    # Gradio command/plan/gallery
├── src/embodied_vla/planner.py   # rule/model prediction→symbolic primitive
├── src/embodied_vla/simulator.py # 2D PNG renderer
├── src/embodied_vla/model_adapters.py # mock/API adapter
└── scripts/                  # synthetic data와 evaluation scaffold
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `README.md:3-5` | scene JSON과 선택적 단일 image |
| 인지·추론 | `README.md:104-145` | endpoint가 target/destination JSON 반환 |
| 정책·액션 생성 | `src/embodied_vla/planner.py:54-89` | 고정 symbolic primitives |
| 학습·데이터 | `README.md:150-213` | synthetic keyword/SFT scaffold |
| 하드웨어·배포 | `src/embodied_vla/simulator.py:32-42` | 물리 없이 2D PNG replay |

## 4. 인상 깊은 코드/패턴

- `README.md:3-5` — 스스로 offline symbolic planning과 mock adapter임을 명시해 범위를 정직하게 제한한다.
- `src/embodied_vla/simulator.py:32-42,47-69` — action은 kinematics/physics가 아니라 2D 좌표와 `holding` 변수를 갱신한다.
- `src/embodied_vla/simulator.py:74-100` — 매 step을 Matplotlib PNG로 저장해 Gradio gallery에 보여준다.
- `README.md:248` — full real-robot VLA가 아니며 다음 단계가 MuJoCo/ROS2 연결이라고 명시한다.

## 5. 내 정의에 어떻게 반영할 것인가

- 이름과 화면만으로 완성도를 판단하면 안 된다는 negative reference로 남긴다.
- command→structured plan→replay의 최소 교육 흐름은 참고할 수 있지만 물리 AI 실증 증거로 재사용하지 않는다.
- 라이선스 부재와 단일 commit 때문에 의존성 후보에서도 제외한다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 15분
- 다음 후보: 실제 LeRobot/Rerun integration
