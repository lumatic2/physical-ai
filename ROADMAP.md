# ROADMAP

> 이 레포의 마일스톤·완료 이력. **포트폴리오 모드** — 완료 기준은 "내가 이해했다"(내부)가 아니라
> "남이 5분 보고 납득한다"(외부). 마일스톤마다 보여줄 수 있는 산출물(showable artifact)이 나온다.
> 마지막 업데이트: 2026-06-15

## 왜 이 레포 (포트폴리오 thesis)

피지컬 AI(embodied AI·로보틱스) 기초 지식을 **입증하는 포트폴리오**.

한 문장: *"피지컬 AI 기초 지식이 있고(지형·이론) → 이론을 내 손으로 직접 실험으로 돌렸고(hands-on)
→ 쓸만한 SW를 만들었다(→ 디지털 트윈 → 조작 가능한 플랫폼 → 실물)."*

피지컬 AI가 2026~2027 더 핫해질 것으로 보고, ① 논문·문헌 기반 지식 축적(`docs/` → `~/vault/`)에서
출발해 ② 직접 돌린 실험과 쓸만한 SW(나아가 실물)로 입증한다.

**현 단계(M9~)**: 트윈을 *관전 데모*에서 *내가 직접 조작하는 플랫폼*으로 격상한다 — 웹에서 마우스+키보드로
기계를 통제하고, 새 임베디먼트·정책을 저마찰로 늘릴 수 있는 확장 가능한 구조로 깎는다.

노출: GitHub 레포 README(개발자·채용) · askewly 블로그 서사 글(통찰·판단) · `~/vault/`(장기 자료집).

## 마일스톤 (한눈에)

| # | 목표군 | 입증하는 것 | 산출물 (showable) | 상태 |
|---|--------|-------------|-------------------|------|
| M1-M3 | 기초 지형 + 첫 실험 | 분야를 이해하고 논문 모델을 직접 실행한다 | `docs/landscape.md`, 5× analysis, exp01 LIBERO | ✅ 압축 |
| M4-M6 | 포트폴리오 1차 + 디지털 트윈 | 실험을 남이 볼 수 있는 도구/데모로 만든다 | README, 블로그 1편, SO-100 웹 트윈 | ✅ 압축 |
| M8-M11 | 브라우저 정책 플랫폼 | 직접 학습한 정책을 웹에서 closed-loop로 돌리고, 새 임베디먼트를 흡수한다 | Go1/G1/Spot 정책 3종, teleop, `add_scene.sh`, dummy-arm | ✅ 압축 |
| M12 | 명령·지형 강건성 검증 | 평지 전진 데모를 넘어 turn/strafe/rough terrain에서 정책 한계를 측정한다 | Go1↔Spot command sweep + rough terrain QA 리포트 + 라이브 데모 | ✅ 완료 |
| M13 | 정책 추가 확장 | M10/M11 플랫폼이 새 정책 패키지를 반복적으로 흡수하는지 확인한다 | G1 rough policy package + byte-parity + live QA | ✅ 완료 |
| M14 | 포트폴리오 2차 패키징 | 기술 디테일을 외부 독자가 5분 안에 이해하게 만든다 | README 압축 개편 + askewly 후속 글 + vault synthesis | ✅ 완료 |
| M7 | 실물 도달 | sim→real을 실제 로봇팔로 닫는다 | SO-101 2-arm + ACT 구매 전 게이트 | 🟨 게이트 완료 |
| M15+ | 다음 목표군 재설계 | 닫힌 마일스톤을 압축하고 다음 포트폴리오/실험 축을 고른다 | 새 ROADMAP 구조 + 후보 우선순위 | ⬜ 다음 세션 |

## 닫힌 마일스톤 압축

### M1-M3 — 지형 파악에서 첫 실행까지 ✅
- **M1**: `docs/landscape.md`로 피지컬 AI 용어·스택·플레이어·reading list 정리.
- **M2**: 핵심 5편을 5섹션 분석하고 ADR 0001로 동작표현 기준 수립.
- **M3**: exp01에서 VLA 로컬 추론·LIBERO 평가를 실행해 H1/H2/H3 PASS와 73% 성공률 확보.

### M4-M6 — 외부에 보이는 포트폴리오와 디지털 트윈 ✅
- **M4**: exp01을 1-command 재현 가능한 도구로 정리하고, exp02에서 π0.5 vs OpenVLA head-to-head를 수행.
- **M5**: public README, askewly 블로그 1편, vault synthesis로 첫 포트폴리오 패키징 완료.
- **M6**: SO-100 웹 디지털 트윈과 pick-and-place replay를 라이브 배포. 5-DOF 기구학 한계와 scripted replay trade-off는 ADR로 박제.

### M8-M11 — 브라우저 정책 플랫폼 ✅
- **M8**: MuJoCo Playground 정책을 학습해 Go1/G1 closed-loop ONNX 정책을 브라우저에서 실행.
- **M9**: WASD 보행, 마우스 EE 텔레옵, 모바일/터치 폴백으로 트윈을 조작 가능한 데모로 전환.
- **M10**: `experiments.json` 단일 소스, `sync_web.py`, `add_scene.sh`, watertight 메시 가드, `ADDING_EMBODIMENTS.md`로 새 임베디먼트 추가 마찰 제거. `dummy-arm`을 bespoke 0줄로 검증.
- **M11**: Spot 정책을 추가해 Go1/G1/Spot 학습 정책 3종을 라이브화. Spot의 81-d obs와 PD gain bake 함정을 ADR 0007로 기록.

---

## 새 목표군: M12-M14

### M12 — 명령·지형 강건성 검증 ✅
> 지금까지는 “브라우저에서 걷는다”를 입증했다. 다음은 “명령이 바뀌고 지형이 거칠어져도 어디까지 버티는가”를 측정한다.

- [x] **Command sweep QA** — Go1·Spot에 대해 vx/vy/vyaw 대표 시나리오(forward, strafe, turn, diagonal)를 실행하고 거리·속도·낙상·NaN·heading drift를 기록. flat 6종 모두 PASS.
- [x] **Keyboard 시연 정리** — M9의 WASD/QE 입력을 QA와 live demo 서사에 연결. `command_sweep.mjs`가 command vector를 직접 주입해 정책 command tracking 검증으로 승격.
- [x] **Rough terrain scene 1종** — 낮은 curb 3개가 있는 `go1-rough-walk`, `spot-rough-walk`를 추가하고 같은 프로토콜로 평가.
- [x] **비교 리포트** — 신규 exp07 README에 Go1↔Spot flat/rough 한계 표, yaw convention, Spot rough drift를 정리.
- 완료 기준: ✅ 로컬+라이브 QA PASS, `?exp=go1-rough-walk`·`?exp=spot-rough-walk` 링크 재현 가능, README/ROADMAP에 결과 표 반영.

### M13 — 정책 추가 확장 ✅
> M12 이후 플랫폼 반복성을 더 보이기 위한 후보. 새 정책 패키지 추가가 연구가 아니라 운영 가능한 루틴인지 검증한다.

- [x] **G1 rough policy package** — `g1/scene_g1_rough.xml` + `g1-rough-walk` registry 추가. Barkour/Go2/H1은 현재 작업트리에 소스·checkpoint·ONNX artifact가 없어 M15 후보로 내림.
- [x] **Runtime diff 최소화** — `rollout_g1.py`를 `python rollout_g1.py [experiment] [seconds]`로 일반화. 기존 `python rollout_g1.py 12`는 `g1-walk`로 유지.
- [x] **Byte-parity** — layout parity `0.00e+00`, bundled scene 첫 5 obs vs golden `0.00e+00`, native 12s 낙상 없음·9.37m.
- [x] **Local/live QA** — WASM load OK, `g1-rough-walk` visual QA PASS, command sweep 6종 PASS, 기존 Go1/G1/Spot 회귀 PASS.
- 완료 기준: ✅ live `?exp=g1-rough-walk` 재현 가능, raw JSON은 [exp08](experiments/08-policy-expansion/README.md)에 박제.

### M14 — 포트폴리오 2차 패키징 ✅
> M8-M12의 기술 디테일을 외부 독자가 읽을 수 있는 구조로 재압축한다.

- [x] README 상단을 “정책 플랫폼 + 검증 하네스” 중심으로 개편.
- [x] askewly 후속 글: command sweep, rough terrain, browser closed-loop 검증 서사. `robot-walk-qa-after-demo`, 2026-06-22 예약 시드.
- [x] vault synthesis: browser robot policy runtime + robustness 결과 통합.
- 완료 기준: ✅ GitHub README, 블로그, vault가 같은 thesis를 말하고 중복/장황함이 줄어든 상태.

### M7 — 실물 도달 (하드웨어 게이트) 🟨
> 코드만으로 끝낼 수 없는 외부 게이트. 구매 전 판단은 닫고, 실제 실물 완료는 하드웨어 확보 후 재개한다.

- [x] **구매 전 게이트** — 신규 구매는 SO-100이 아니라 SO-101 leader+follower 2-arm teleop로 좁힘. [ADR 0008](docs/adr/0008-m7-real-arm-gate.md), [exp09](experiments/09-real-arm-gate/README.md).
- [x] **첫 task 축소** — M6에서 확인한 5-DOF top-down lift 한계를 반영해 stacking이 아니라 tabletop pick/place로 시작.
- [x] **정책 경로** — ACT-first. LeRobot 기반 데이터 수집 → ACT 학습 → held-out pose eval → reality-gap 회고.
- [ ] **외부 입력 필요** — 예산/배송/작업공간/카메라/조립 시간 확보.
- 완료 기준(실물): 실물 팔 pick/place 수행 영상 + dataset/train/eval log + reality gap 회고.

### M15+ — 다음 목표군 재설계 ⬜
> M12-M14와 M7 게이트까지 닫힌 상태. 다음 세션에서 로드맵을 다시 짜고 새 마일스톤 묶음을 정의한다.

- 후보 A: **새 정책 학습 확장** — Barkour/Go2/H1 등 Playground policy를 새로 학습해 train→ONNX→native parity→web live QA까지 반복.
- 후보 B: **실물 M7a bring-up** — SO-101 2-arm 구매가 확정되면 LeRobot calibration, data capture, ACT baseline으로 이동.
- 후보 C: **포트폴리오 배포면 정리** — 예약 블로그 공개 후 README/askewly/vault 간 메시지 drift 점검.
- 다음 세션 완료 기준: M15+ 목표군과 2~4개 세부 마일스톤을 새 ROADMAP 구조로 확정.

## 완료 이력
- 2026-06-09 — M1 지형 파악. `docs/landscape.md`(정의·용어 11종·4레이어 스택·플레이어 맵·reading list 15개).
- 2026-06-09 — M2 레퍼런스 정독. 5편 5섹션 분석 + ADR 0001 동작표현 3축 + vault 이전.
- 2026-06-09 — M3 첫 실험. `experiments/01` VLA 로컬 추론 + LIBERO 평가, H1·H2·H3 PASS(success 73%), tf↔EGL 세그폴트를 REST 서버/클라 분리로 해소, 마찰 6건 박제. **로드맵을 포트폴리오 모드로 재설계(M4~M6 추가).**
- 2026-06-11 — **M4 완주**. Track A(experiment 01 도구화) + Track C(π0.5 비교, experiment 02). 동작표현 2축 실측: matched 3 task에서 flow-matching(π0.5) 98.7% vs 이산토큰(OpenVLA) 73.3%, Fisher p<1e-3. openpi 비-Docker(서버 cu128 / 클라 py3.8 별도 venv), JAX 다운 9p 실패→HF 포트 fallback. Codex adversarial-review가 task-모집단 과장(10 vs 3) 잡아내 matched-subset으로 교정 후 push.
- 2026-06-11 (후속) — **M4 잔여 caveat 2건 해소**. ① setup.sh 클린룸 검증(빈 venv) — requirements 누락 의존 2건(accelerate·LIBERO런타임) 잡아 보정(`a9823dd`). ② full apples-to-apples 재측정: OpenVLA 10task×50=500ep(77.4%) + 공식 JAX `pi05_libero` 변환(WSL 순수-python GCS로 9p 우회)으로 π0.5 공식 500ep(98.4%). **대칭·공식 head-to-head: +21pp, Fisher p=1.4e-27, CI 비겹침**. 초안 matched OpenVLA 73.3%(11/15)는 소표본 과소추정이었음(n=150→89.3%)을 정직 교정.
- 2026-06-11 (후속) — **M5 완주**. ① public README 포트폴리오 랜딩 재설계(`f0d58ba`). ② askewly 블로그 글 "논문은 안다고 착각하게 만듭니다" anti-AI verify PASS → 라이브 발행(`dcebaf8`+KV). ③ vault: M2~M4 통합 synthesis 노트 작성 + Research 00-INDEX에 physical-ai 섹션 등록(고립 해소). 남은 건 M6(실물 로봇팔).
- 2026-06-12 — **M6 대부분 완주**(정책 replay만 남음). M6를 하드웨어 게이트에서 분리(M6 디지털 트윈 / M7 실물), [ADR 0004](docs/adr/0004-digital-twin-stack.md) 스택 결정. SO-100(Menagerie `trs_so_arm100`, 메인 머지 확인) MuJoCo 로드 스모크 PASS → 오프스크린 렌더 mp4 → `experiments/03-digital-twin`. **웹 인터랙티브 3D**: zalo/mujoco_wasm(공식 DeepMind WASM) 기반 자체완결 정적 앱 `web/`, 홈 키프레임 직립·반응형. Vercel 배포 중 node_modules 미서빙 함정 → deps CDN화로 순수정적 해소. **커스텀 도메인 라이브: physical-ai-arm.askewly.com**(CF_DNS_TOKEN으로 CNAME). askewly.com Products에 트윈 카드+robot-arm 아이콘 추가(자동배포). 커밋 `4628bfc`·`84f3fa2`·`704e8ed`·`f66d0a0`.
- 2026-06-12 (후속) — **M6 완주**(정책 롤아웃 replay). sweep → scripted **pick-and-place 3단 스택**. 블록을 free-joint로 바꾸고 타깃 패드 추가(reachable 밴드 y<−0.14로 재배치 — Rotation 한계 회피), `make_pick_trajectory.py`가 damped-LS Jacobian IK로 Cartesian 웨이포인트를 풀고 집는 순간 weld relpose 주입으로 carry·놓은 블록은 타워 포즈로 freeze → qpos 385프레임 기록. 데스크탑(`render_twin.py`)·웹(`main.js`) 모두 **운동학 재생**(qpos+mj_forward)이라 mp4==웹. 웹은 자동재생 루프 + "▶ Replay rollout" interactive 토글, 카메라를 워크스페이스 중심으로 재프레이밍. 검증: IK 0.1mm, smoke PASS(nq=27), 라이브 콘솔 0 에러. 커밋 `70b1fde`·`3285e2e`. (정직: 학습 정책 아닌 scripted replay — ADR 0004 trade-off)
- 2026-06-12 (후속2) — **M6 그리퍼–큐브 상호작용 다듬기 + 기구학 한계 박제**. weld carry가 기울기·스냅·관통을 내서 kinematic 결합으로 교체(`c4df75f`), 웹에 grab-to-take-over(재생 중 잡으면 자동 interactive 전환)(`97788e2`). 사용자 지적("집게가 큐브 관통, 잡기/잡힘 디커플") 대응으로 6-DOF 자세 IK + 실제 물리 집기를 조사 → **단일 큐브 물리 집기는 됨**(마찰 2.5+스퀴즈+top-down IK 검증)이나 **이 5-DOF SO-100은 top-down 파지 자세를 들어올림 높이에서 유지 불가**(top-down 도달은 테이블 z≈0.018뿐, z≳0.11 IK 잔차 50~250mm) → 완전 인과적 pick-lift-stack 불가 박제. 사용자 선택으로 **"시각적 결합"** 채택: grasp point를 손끝 중점으로, 운반 중 jaw를 큐브 폭까지 닫아 손가락이 큐브에 실제 접촉(관통 해소)(`f4df921`). 라이브 재배포, 8커밋 push 완료(`558777f`).

- 2026-06-12 (후속3) — **M8 착수: 트윈을 학습 정책 sandbox로**. 저가팔 구매 비현실 → M7(실물) 보류, sim sandbox로 방향 전환. ① **config-driven 하네스 리팩터**(`0ecb94f`): SO-100 하드코딩(smoke/render/web)을 `experiments.json` 레지스트리 + `harness.py` + 범용 물리 레코더 `record_trajectory.py`로 일반화. `make_pick_trajectory.py`(IK)는 불변. humanoid-settle을 bespoke 0줄로 record→smoke→render→웹(`?exp=`) 통과시켜 일반성 실증. 라이브 재배포(기본값 SO-100 무변화, 0 에러). ② **축 설계 [ADR 0005](docs/adr/0005-learned-policy-sandbox.md)**(`b98198c`): A+B 결합(갤러리+직접학습), 파일럿=Go1 보행, MuJoCo Playground 학습→ONNX→onnxruntime-web closed-loop. ADR 0004 되돌림 조건 (a) 발동. 외부 리서치로 경로 검증(Playground Go1 5분 학습·50Hz ONNX·RSS2025 브라우저 데모). obs parity·JAX-on-Blackwell(rsl_rl 폴백)이 핵심 리스크.
- 2026-06-13 — **M8 완주: 직접 학습한 정책이 브라우저에서 Go1을 걷게 한다**. **Phase 1**([exp 04](experiments/04-go1-rl-walk/README.md), `66f7ff5`): WSL+RTX5090서 Playground `Go1JoystickFlatTerrain` PPO 200M **8.8분**(reward 0.001→29.7) → 손작성 ONNX(onnx vs jax parity 4.8e-6) → native mujoco closed-loop 12s·11.8m·0.99m/s. 함정: brax0.14.2↔jax0.10 비호환→**jax 0.9.2 다운핀**(sm_120 PASS), impl=warp→jax. **Phase 2**(`5f74ead`): go1 씬을 `web/assets/scenes/go1/`에 self-contained 번들, `policy` 블록 + `rollout_policy.py`(번들 씬 closed-loop). 번들 씬 rollout 첫5 obs == 학습 golden **0.0**(씬 바이트 동일). 함정: mj_step 후 sensordata 1-substep stale. **Phase 3**(`c535311`): `onnxruntime-web` 브라우저 closed-loop(obs→onnx→ctrl→mj_step@50Hz, 별도 제어 루프), 카메라가 free-joint 루트 추적. JS obs builder byte-parity **0.0**. 헤드리스+node서버로 검증(throttle 우회 400스텝 7.9m). 메시 데시메이트(15MB→5.9MB)로 Vercel 배포(`bd7824a`). **라이브 `?exp=go1-walk` 보행 7.84m + 0 콘솔에러** 확인. obs parity(최대리스크) 단일 진실원천(obs_spec→번들씬→policy.indices→JS)으로 해소. Codex adversarial 교차검증으로 default_pose 누락 + golden fixture 보강(`fef8d5e`).

- 2026-06-14 — **M8 후속: 라이브 다듬기 + 갤러리 폭 + 자동 시각 QA**. ① go1 비주얼 메시 깨짐 수정 — `bd7824a`가 5메시를 6000면 고정 데시메이트(trunk 112k→6k, 95% 손실)해 점 무더기로 렌더되던 걸, trimesh weld 후 per-mesh 예산(trunk 20k 등 2.45MB) 재데시메이트(`f3a6921`). ② **자동 시각 QA 하네스**(`7b46ece`): `window.demo.qaStep`(결정론적 N스텝+render, 헤드리스 setTimeout throttle 우회) + playwright `qa/visual_check.mjs`(serve/--live, 스크린샷+보행 diagnostics assert) → Claude가 육안 대신 라이브 자가검증. 이걸로 go1 메시 깨짐을 잡음. ③ go1 command 조이스틱 슬라이더(vx/vy/vyaw)(`069e4f1`). ④ 배포 SHA 파일업로드 API 전환(`42a302b`) — 인라인 단일-POST ~10MB 캡 제거로 갤러리 확장 가능. ⑤ **Shadow Hand 갤러리 추가**(`fa9d1e3` + `.obj` 배포 누락 404 수정 `9b9c8f9`): 손가락 굴곡 scripted ctrl-sweep replay(`record_ctrl_sweep.py`), 메시 replay용 `qaSeek` QA 훅. ⑥ C3 그라운드워크(`f9aa01f`): 씬 로더 하드코딩 목록→`manifest.json`(gen_scene_manifest.py), 범용 `decimate_meshes.py`, QA goto networkidle→domcontentloaded(무거운 씬). **라이브 갤러리 4종 전부 QA PASS**(go1·shadow-hand·humanoid·so100). Spot·Panda·G1은 원본 Meshlab OBJ의 mujoco-js 로드(trimesh 재export로 해결)·표면 품질(점박이, 공유 렌더 z-fighting/노멀 의심) 튜닝이 모델마다 비자명(Panda서 확인)이라 별도 세션 보류. 7커밋 push(`20c9ab9..f9aa01f`).

- 2026-06-14 (후속2) — **갤러리 폭 완성(축 A) + G1 휴머노이드 보행 정책(축 B)**. ① **Spot·G1 floating-base settle** 추가(position kp keyframe hold), **Franka Panda** 추가 — 지난 세션 보류였던 "표면 점박이"를 **데스크탑 MuJoCo 렌더로 격리**해 web이 아닌 메시 데이터 문제로 확정(이전 "공유 렌더 코드" 가설 오진), 원인은 `fast_simplification`이 Franka의 non-watertight 코스메틱 shell을 붕괴(see-through 슬라이버)시킨 것 → 총 134k면뿐이라 **simplify 없이 바이너리 STL(6.7MB)** 로 변환해 해소. 부수 수정: mujocoUtils 바이너리 확장자 대소문자 무관(G1 `.STL`). 갤러리 **8종**(`02765e5`·`cb5a439`). ② **G1 휴머노이드 보행 정책**([exp 05](experiments/05-g1-rl-walk/README.md), `e6dd6c5`): Go1(exp 04) 파이프라인을 휴머노이드에 적용 — PPO 200M 46.5분(reward −6.4→+14.8) → ONNX(parity 2.1e-6) → native 9.38m 보행 → 번들 씬 **obs byte-parity 0.00e+00**(layout+scene) → 브라우저 live closed-loop 5.0m·0에러. **난관=obs parity**: Go1 48-d와 달리 103-d·command 중간·**gait phase clock**(stateful 외부 클록 native/desktop/JS 3곳 일치). main.js obs builder를 `obs_layout` 기반 일반 빌더로(go1·G1 한 경로, go1 회귀 PASS). 학습 정책 임베디먼트 **2종**(4족 Go1 + 휴머노이드 G1). ③ 패키징: README(갤러리 8종·학습정책·마일스톤 현행화)·exp 03/05 README·ROADMAP 갱신 + **askewly 블로그 2편째 "하드웨어 없이 로봇을 걷게 하는 법"** 발행(anti-AI verify PASS, 큐리 커버, R2+KV 라이브). 커밋 `02765e5`·`cb5a439`·`e6dd6c5`·`65a676b` origin push 완료.

- 2026-06-14 (후속3) — **M9 인터랙티브 텔레옵 구현·로컬 QA 완주**(배포 대기). 트윈을 *관전*에서 *직접 조작*으로 격상. **step1** 키보드 보행 조종(WASD=vx/vy, Q/E=vyaw hold-to-drive→`pol.command` 직결, 슬라이더 동기)(`244d418`) — QA `--keys` 모드 신설, go1 5.9m·g1 3.4m PASS. **step2** 조작 안내 오버레이(bottom-left, 임베디먼트별)(`a87bb49`) — 드래그-힘은 이미 정책+물리 루프 양쪽 배선 확인, 실질은 discoverability. **step3** 마우스 EE 텔레옵(`5071668`) — 그리퍼 드래그→**유한차분 Jacobian damped-LS IK**(wasm `mj_jacBody` 출력인자 회피, qpos/xpos+mj_forward만 사용). SO-100·Panda `teleop:true`, 비-joint 액추에이터(Panda 텐던 그리퍼) 제외·관절/ctrl 클램프. QA `--teleop`: so100 잔차 1e-16(완전추종)·panda 0.141→0.080(컨토트 sweep-start 한계). 5-DOF 도달 한계는 정직 추종(M6/ADR 0004). **step4** 모바일/터치 폴백(`8090888`) — coarse pointer 감지→안내를 슬라이더/손가락으로(WASD 숨김), QA `--mobile`(390×844) go1·so100-텔레옵 PASS. 4스텝 4커밋. **Vercel 재배포 후 라이브 QA PASS**(키보드 go1 4.4m·so100 텔레옵 잔차 0) → https://physical-ai-arm.askewly.com 반영.
- 2026-06-15 — **M12 완주: 명령·지형 강건성 검증**. `command_sweep.mjs`로 Go1·Spot flat/rough 6시나리오(forward, strafe-left/right, turn-left/right, diagonal-left)를 측정하고 yaw/command diagnostics를 `qaStep`에 추가. rough curb scene(`go1-rough-walk`, `spot-rough-walk`)은 1/2/3cm step으로 고정해 로컬+라이브 모두 낙상·NaN·콘솔에러 0 PASS. 라이브 alias: `?exp=go1-rough-walk`, `?exp=spot-rough-walk`. 결과와 raw JSON은 [exp 07](experiments/07-command-terrain-robustness/README.md)에 박제.
- 2026-06-15 — **M14 완주: 포트폴리오 2차 패키징**. README를 “검증 가능한 브라우저 로봇 정책 플랫폼” 중심으로 재압축하고 M12 rough command QA를 상단 노출. askewly 글 `robot-walk-qa-after-demo` 작성·큐리 커버 생성·R2 업로드·KV targeted 예약 시드(2026-06-22 KST 공개). vault synthesis `2026-06-15-browser-robot-policy-runtime.md`에 M12 command/terrain robustness 통합.
- 2026-06-15 — **M13 완주: 정책 추가 확장**. `g1-rough-walk` policy package 추가. G1 rough scene + registry + `rollout_g1.py [experiment]` 일반화, native byte-parity 0.0, 로컬+라이브 visual/command QA PASS, 기존 Go1/G1/Spot 회귀 PASS. raw JSON은 [exp 08](experiments/08-policy-expansion/README.md).
- 2026-06-15 — **M7 구매 전 게이트 완료**. SO-100 신규 구매는 제외하고 SO-101 leader+follower 2-arm + LeRobot + ACT-first로 실물 경로를 좁힘. 첫 task는 stack이 아니라 tabletop pick/place. 실제 M7 완료는 예산·배송·작업공간·조립 시간 확보 후 재개. [ADR 0008](docs/adr/0008-m7-real-arm-gate.md), [exp 09](experiments/09-real-arm-gate/README.md).

## 의사결정 이력
"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 *의도적 제외*는 `docs/adr/`에 ADR로.
