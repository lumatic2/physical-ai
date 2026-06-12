# 0004 — M6 디지털 트윈 스택: SO-100 MJCF + MuJoCo WASM 웹 replay

- Status: Accepted (2026-06-12)
- 근거 reference: TheRobotStudio/SO-ARM100, google-deepmind/mujoco(wasm), zalo/mujoco_wasm, lachlanhurst/so100-mujoco-sim, huggingface/lerobot
- 관련: [[0002-act-deferred-to-m6]] (ACT는 실물 모방학습 자리), M6 디지털 트윈 / M7 실물 분리(ROADMAP 2026-06-12)

## Context

M6를 하드웨어 게이트(구 M6 → 현 M7)에서 떼어내 "SO-100 팔을 sim에 세우고 정책 롤아웃을 웹에서
인터랙티브 3D로 보여준다"로 재정의했다(ROADMAP 2026-06-12). 착수 전에 ① SO-100 sim 모델을 어디서 받고
② 무엇을 트윈 위에 올리며 ③ 웹 인터랙티브 3D를 무엇으로 렌더할지를 정해야 한다. 외부 리서치(2026-06-12) 결과:

- **모델**: 공식 `TheRobotStudio/SO-ARM100`이 URDF/XACRO + **MJCF(MuJoCo XML)** + USD(IsaacSim)를 직접 제공한다
  (SO-100/SO-101 양쪽, 신/구 캘리브레이션). Apache-2.0, 활발(220 커밋). 접근 2026-06-12.
  `mujoco_menagerie`의 SO-ARM100(`trs_so_arm100`)도 **메인에 정식 포함됨**(scene.xml + so_arm100.xml + assets,
  6관절 Rotation/Pitch/Elbow/Wrist_Pitch/Wrist_Roll/Jaw) — 2026-06-12 로컬 로드 스모크로 검증(`tmp/smoke_so100.py` PASS).
  접근 2026-06-12.
- **웹 렌더**: `zalo/mujoco_wasm`은 이제 자체 컴파일이 아니라 **DeepMind 공식 MuJoCo WASM 바인딩**(MuJoCo 3.3.8)을
  쓰는 데모 스위트로, MJCF를 Emscripten FS에 써서 로드하고 Three.js로 렌더한다. MIT. 접근 2026-06-12.
  → 같은 MJCF를 *실제 물리째* 브라우저에서 돌릴 수 있어 "sim"과 "웹 시각화"가 한 산출물로 합쳐진다.
- **참조 구현**: `lachlanhurst/so100-mujoco-sim`(MIT)이 Menagerie SO-100 자동 다운로드 + 실↔sim 동기·녹화·재생을
  이미 구현. 단 **teleop/replay 전용**으로 학습된 정책(ACT/VLA)은 돌리지 않는다. 접근 2026-06-12.
- **정책을 sim에서**: LeRobot `il_sim`(sim 모방학습) 경로가 있으나 기본 대상은 ALOHA/gym 환경이고 SO-100용은
  `gym-so100-c`·`EE5108-DigitalTwins/lerobot_mujoco_sim` 같은 커뮤니티 환경을 붙여야 한다(밑바닥 훈련 = GPU-시간).
  또한 **VLA/ACT 추론을 브라우저에서 직접 돌리는 한 레포는 없다** — WASM은 물리+렌더만 담당. 접근 2026-06-12.

## Decision

**M6 디지털 트윈을 다음 스택으로 조립하고, "정책을 무엇으로 돌리나"는 replay-first로 시작한다.**

1. **모델**: Menagerie `trs_so_arm100`(DeepMind 큐레이션, 메인 포함 확인)을 1차 모델로 사용. 캘리브레이션
   변형·USD 등 추가 자산이 필요하면 공식 `TheRobotStudio/SO-ARM100`을 보조 출처로. (2026-06-12 Menagerie 로드 스모크 PASS)
2. **정책(롤아웃)**: **trajectory replay 우선**. sim에서 미리 롤아웃한 궤적을 웹에서 재생한다. ACT를
   SO-100 차원으로 sim-학습하는 무거운 경로는 *M6 위에 얹는 후속*으로 미루고, ACT의 본 무대인 실물
   모방학습은 [[0002-act-deferred-to-m6]]대로 M7에서.
3. **웹 인터랙티브 3D**: `zalo/mujoco_wasm`(공식 DeepMind WASM 바인딩)으로 같은 MJCF를 브라우저에서 렌더 +
   롤아웃 replay. 관절 조작만 필요한 경량 뷰가 필요하면 `gkjohnson/urdf-loaders`를 폴백으로.

## Consequences

- **(+)** "브라우저에서 도는 SO-100 트윈"이라는 showable artifact가 정책 학습이라는 무거운 결정 *이전에* 나온다 —
  포트폴리오 thesis(showable)에 부합하고 M6 착수가 하드웨어·GPU-시간에 막히지 않는다.
- **(+)** sim 모델·웹 렌더 모두 MJCF 한 자산으로 통일 — sim↔web 사이 모델 변환·드리프트가 없다.
- **(+)** M7(실물)로 직결: 같은 SO-100 모델·LeRobot 데이터 포맷을 쓰므로 teleop 데이터·ACT 학습이 트윈 위에 그대로 얹힌다.
- **(−)** 첫 산출물의 트윈은 "정책이 추론하며 움직이는" 게 아니라 "미리 만든 궤적을 재생"하는 것 — 데모로는 충분하나
  *live policy in browser*는 아님(정직 표기 필요).
- **(+)** Menagerie `trs_so_arm100` 메인 포함·로드 검증 완료(2026-06-12) → 깨끗한 큐레이션 모델을 1차로 사용.
- **되돌림 조건**: (a) onnx 등으로 경량 정책의 브라우저 추론이 현실적이면 replay → live inference로 승격.
  (b) `il_sim`+`gym-so100`이 충분히 성숙하면 ACT sim-학습을 M6 본 단계로 끌어올려 supersede.
