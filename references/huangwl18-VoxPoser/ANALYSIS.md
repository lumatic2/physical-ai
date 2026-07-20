# huangwl18/VoxPoser 분석

> 클론: https://github.com/huangwl18/VoxPoser (`e3a4c9e57b6e`, 2026-07-20 접근) · 라이선스: MIT

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

언어 지시를 하위 과제로 분해하고 3D value map을 합성해 waypoint와 controller action으로 바꾸며, value map과 planned trajectory를 Plotly로 보여주는 **계층형 언어-조작 연구 하네스**다.

## 2. 디렉터리 지도 (핵심 폴더만)

```text
VoxPoser/
├── src/LMP.py            # 언어 모델 프로그램과 task decomposition
├── src/interfaces.py     # voxel map·planner 호출 API
├── src/planners.py       # value map 기반 waypoint 생성
├── src/controllers.py    # waypoint 실행
├── src/visualizers.py    # 3D value map·path Plotly viewer
└── src/envs/             # RLBench 환경 adapter
```

## 3. 아키텍처 레이어 매핑

| 레이어 | 위치 (파일:줄) | 내용 |
|---|---|---|
| 입력·센서 | `README.md:15,77-79` | RLBench object mask 또는 외부 detection/segmentation/tracking |
| 인지·추론 | `README.md:56-57` | LLM program이 instruction을 분해하고 value map 합성 |
| 정책·액션 생성 | `README.md:58-60` | waypoint planner, controller, MPC |
| 학습·데이터 | 해당 없음 | zero-shot synthesis 중심 |
| 하드웨어·배포 | `README.md:75-79` | environment API 교체로 real robot 연결 |

## 4. 인상 깊은 코드/패턴

- `README.md:56-60` — 언어 분해, spatial value map, waypoint, controller를 분리해 “판단”과 “실행”의 출처를 구조적으로 보여준다.
- `src/visualizers.py:8-10,81-111` — target map, cost map, start, planned path를 같은 3D plot에 겹쳐 결과가 아니라 행동 선택 근거를 관찰하게 한다.
- `README.md:15` — 공개 코드는 실제 perception pipeline을 포함하지 않고 RLBench mask를 사용한다고 명시한다. claim boundary의 좋은 사례다.

## 5. 내 정의에 어떻게 반영할 것인가

- LAB2의 계층형 비교 lane에서 `semantic observation → selected skill/target → planned path → controller result` 구조를 차용한다.
- VoxPoser 전체를 주 실행기로 쓰지는 않는다. LIBERO/LeRobot 기반 VLA episode와 직접 호환되지 않고 perception도 공개 코드에 빠져 있다.
- value map/trajectory는 실제 산출된 경우만 표시하며 설명용으로 사후 생성하지 않는다.

---

## 메타

- 수집일: 2026-07-20
- 소요 시간: 약 20분
- 다음 후보: Code as Policies, RLBench visualization
