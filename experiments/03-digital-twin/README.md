# 03-digital-twin — SO-100 디지털 트윈 (MuJoCo, sim, 하드웨어 불필요)

> `experiments/03-digital-twin/README.md` — M6 디지털 트윈의 1차 산출물(PoC).
> 거버넌스: [ADR 0004](../../docs/adr/0004-digital-twin-stack.md) — 트윈 스택 선택(SO-100 MJCF + MuJoCo WASM 웹 replay, 정책 replay-first).
> 짝: M7 실물([ADR 0002](../../docs/adr/0002-act-deferred-to-m6.md) — ACT는 실물 모방학습 자리).

저가 로봇팔 SO-100을 **사기 전에** sim에 세우고, consumer Windows에서 정책 롤아웃을 렌더해 포트폴리오로
보여주는 게 목표. 하드웨어 없이 sim→real 직전까지.

![SO-100 twin sweep](media/so100_twin.gif)

## 1. 목표

- SO-100(`trs_so_arm100`) MJCF를 MuJoCo에 로드해 **6관절(Rotation·Pitch·Elbow·Wrist_Pitch·Wrist_Roll·Jaw)** 트윈을 세운다.
- consumer Windows에서 **오프스크린 GL 렌더**로 움직이는 트윈 영상(mp4/gif)을 낸다 — 웹/README 임베드용.
- 다음 단계(웹 인터랙티브 3D = MuJoCo WASM, 정책 학습)의 기반 자산을 레포에 고정한다.

## 2. 방법

- **모델**: MuJoCo Menagerie(DeepMind 큐레이션) `trs_so_arm100`. `setup.sh`가 sparse-checkout으로 그 폴더만 받아
  `vendor/`(비트래킹)에 둔다. 커스텀 씬 [`scene_twin.xml`](scene_twin.xml)이 `<include>`로 모델을 불러오고
  색 블록 3개(집기 태스크 맥락) + 고해상도 offscreen 프레임버퍼(1280×960)를 더한다.
- **모션**: **replay-first** (ADR 0004 Decision §2). 학습된 정책이 아니라 *스크립트 pick-and-place
  궤적*을 재생한다 — [`make_pick_trajectory.py`](make_pick_trajectory.py)가 Jacobian IK로 팔의 Cartesian
  웨이포인트(블록 위 hover→하강→집기→들기→이동→스택→복귀)를 풀고(mj_step 서보), **블록은 물리가 아니라
  KINEMATIC으로 구동**한다 — rest/carried/placed 3상태로, carried는 그리퍼 grasp point에 *항상 수직으로*
  핀, placed는 정확한 타워 높이로 freeze. 전체 qpos(팔 6 + 블록 3×7)를 프레임마다
  [`pick_trajectory.json`](pick_trajectory.json)에 기록. ACT를 SO-100 차원으로 sim-학습하는 무거운 경로는 후속.
- **재생**: 데스크탑·웹 모두 기록 qpos를 **운동학적으로 재생**(qpos 세팅 + `mj_forward`)한다 → mp4 == 웹 동일,
  접촉·마찰 튜닝이 재생에 새지 않음.
- **렌더**: `mujoco.Renderer` 오프스크린(창 없음). Windows 네이티브 GL에서 동작 — WSL 우회 불필요.

```bash
bash setup.sh                          # SO-100 모델 다운로드 (vendor/, 1회)
pip install -r requirements.txt        # mujoco·imageio
python smoke_twin.py                   # 빠른 헤드리스 게이트 (로드+FK+액추에이션), exit 0 = PASS
python make_pick_trajectory.py         # pick_trajectory.json 생성 (스크립트 롤아웃)
python render_twin.py                  # media/so100_twin.mp4 생성 (궤적 재생)
```

> **새 임베디먼트/정책 추가**(M10 확장 플랫폼): 파이프라인 코드 0줄로 갤러리에 올리는 N단계 가이드 →
> [`ADDING_EMBODIMENTS.md`](ADDING_EMBODIMENTS.md). 한 커맨드 `add_scene.sh <exp>` 가
> manifest→record→smoke→loadtest→render→sync→visual 체인을 fail-fast로 돈다.

## 3. 결과

- **로드 스모크 PASS** (`smoke_twin.py`): nq=27(팔 6 + free-joint 블록 3×7), nu=6, FK 풀림, ctrl 인가 시 Moving_Jaw |Δ|≈0.14m 이동.
- **궤적 생성 PASS** (`make_pick_trajectory.py`): IK 잔차 max 0.1mm, 3블록을 (0.14,−0.26)에 z=0.018/0.054/0.090으로 정렬 스택, 385프레임/12.8초.
- **렌더 PASS** (`render_twin.py`): 1280×960, 385프레임 mp4 — 홈→집기→3단 스택 육안 확인.
- **웹 replay PASS** (라이브): 콘솔 0 에러, 자동재생 루프, 3단 스택 프레이밍, "▶ Replay rollout" 토글로 interactive 전환.
- 산출물: [`media/so100_twin.mp4`](media/so100_twin.mp4) (고화질) + [`media/so100_twin.gif`](media/so100_twin.gif) (README 임베드용) + [`pick_trajectory.json`](pick_trajectory.json) (단일 진실원천).

## 4. 통찰 / 한계 (정직)

- ✅ **하드웨어·GPU-시간 없이** "집고 쌓는 SO-100 트윈" showable artifact가 나온다 — M6를 구매 게이트에서 떼어낸 게 유효.
- ✅ Menagerie `trs_so_arm100`는 **메인에 정식 포함**(검증 2026-06-12) — 깨끗한 큐레이션 모델을 1차로 씀.
- ✅ **정책 롤아웃 replay 완료** — sweep → 스크립트 pick-and-place 3단 스택. 블록은 free-joint, IK로 푼 팔이 집어 옮긴다.
- ⚠ **여전히 학습 정책이 아니라 scripted replay** — "정책이 추론하며 집는" live policy는 아님(ADR 0004 trade-off, 정직 표기). IK 웨이포인트 + 운동학 재생.
- ⚠ 재생 중 큐브는 **물리가 아니라 kinematic 결합** — 손끝 중점에 핀하되 운반 중 집게를 큐브 폭까지 닫아 손가락이 큐브 면에 *실제 접촉*(관통·틈 없음)하며 함께 이동. 데스크탑 mp4 == 웹.
- ⚠ **왜 인과적 물리가 아닌가(검증된 기구학 한계)**: 단일 큐브 물리 집기·들기는 됨(검증). 그러나 이 5-DOF SO-100은 *top-down 파지 자세를 들어올림 높이에서 유지 불가*(top-down은 테이블 높이에서만 도달; z≳0.11에선 IK 잔차 50~250mm). → 완전 인과적 pick-lift-stack은 이 팔로는 불가 → 운동학 결합으로 그 *모습*을 재현. **interactive 토글(체크 해제)에서만 live 물리** — 블록 드래그 시 실제 충돌·낙하, Actuators 슬라이더로 관절 구동.
- ✅ **웹 인터랙티브 3D + 공개 호스팅** → [`web/`](web/README.md): 같은 MJCF를 브라우저에서(mujoco_wasm) 자동재생 루프 + 반응형. **라이브: https://robotics.askewly.com**.

## 출처

- 모델: [google-deepmind/mujoco_menagerie · trs_so_arm100](https://github.com/google-deepmind/mujoco_menagerie/tree/main/trs_so_arm100) (Apache-2.0, 접근 2026-06-12)
- 원본 팔: [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) (Apache-2.0)
- 참조 트윈 구현: [lachlanhurst/so100-mujoco-sim](https://github.com/lachlanhurst/so100-mujoco-sim) (MIT)
- vault: `10-Resources/10.10-Research/physical-ai/so100-digital-twin-stack-2026-06-12.md`
