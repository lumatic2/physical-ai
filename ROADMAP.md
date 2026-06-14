# ROADMAP

> 이 레포의 마일스톤·완료 이력. **포트폴리오 모드** — 완료 기준은 "내가 이해했다"(내부)가 아니라
> "남이 5분 보고 납득한다"(외부). 마일스톤마다 보여줄 수 있는 산출물(showable artifact)이 나온다.
> 마지막 업데이트: 2026-06-14

## 왜 이 레포 (포트폴리오 thesis)

피지컬 AI(embodied AI·로보틱스) 기초 지식을 **입증하는 포트폴리오**.

한 문장: *"피지컬 AI 기초 지식이 있고(지형·이론) → 이론을 내 손으로 직접 실험으로 돌렸고(hands-on)
→ 쓸만한 SW를 만들었다(→ 디지털 트윈 → 실물)."*

피지컬 AI가 2026~2027 더 핫해질 것으로 보고, ① 논문·문헌 기반 지식 축적(`docs/` → `~/vault/`)에서
출발해 ② 직접 돌린 실험과 쓸만한 SW(나아가 실물)로 입증한다.

노출: GitHub 레포 README(개발자·채용) · askewly 블로그 서사 글(통찰·판단) · `~/vault/`(장기 자료집).

## 마일스톤 (한눈에)

| # | 마일스톤 | 입증하는 것 | 산출물 (showable) | 상태 |
|---|---------|------------|-------------------|------|
| M1 | 지형 파악 | 분야 전체를 매핑한다 | `docs/landscape.md` | ✅ |
| M2 | 레퍼런스 정독 + ADR | 1차 문헌을 비판적으로 읽는다 | 5× `ANALYSIS.md`, ADR 0001 | ✅ |
| M3 | 첫 실험 (이론 직접 실행) | 논문 모델을 내 GPU에서 실행·평가한다 | `experiments/01` (H1·H2·H3 PASS, LIBERO 73%) | ✅ |
| M4 | 쓸만한 SW 승격 (flagship) | 실험을 남이 쓸 도구/데모로 만든다 | 클린 README + 1-command 재현 + 2모델 결과표 | ✅ |
| M5 | 포트폴리오 패키징 | 5분 안에 실력이 읽힌다 | public README + 블로그 글 1편 + vault 정리 | ✅ |
| M6 | 디지털 트윈 (sim) | 하드웨어 없이 sim→real 직전까지, 웹에서 보여준다 | 인터랙티브 3D 트윈 [라이브](https://physical-ai-arm.askewly.com) + 정책 롤아웃 replay(pick-and-place 3단 스택) | ✅ |
| M8 | 학습 정책 sandbox (sim) | 직접 학습한 정책이 브라우저에서 몸을 제어한다 | live Go1 보행(onnxruntime-web) + config-driven 하네스 | ✅ |
| M7 | 실물 도달 (하드웨어 게이트, 보류) | sim→real 한 바퀴, 실물까지 만든다 | SO-100 저가팔 + ACT, 수행 영상 | ⬜ |

### M1 — 지형 파악 ✅
- [x] 핵심 용어·taxonomy·플레이어 맵·reading list 15개 → `docs/landscape.md`
- 완료: 2026-06-09

### M2 — 레퍼런스 정독 ✅
- [x] 핵심 5편(OpenVLA·π0·ACT·OXE·VLA서베이) 5섹션 분석 + [ADR 0001](docs/adr/0001-vla-action-representation.md) + vault 이전
- 완료: 2026-06-09

### M3 — 첫 실험 ✅
- [x] 아이디어 5개 문서화 → [docs/m3-ideas.md](docs/m3-ideas.md)
- [x] #1 VLA 로컬 추론 + 시뮬 평가 → `experiments/01-vla-local-eval` (H1 15GB·H2 168ms·H3 73%, REST 서버/클라 분리, 마찰 6건 박제)
- 완료: 2026-06-09

### M4 — 쓸만한 SW로 승격 (flagship) ✅
- **flagship (채택: A+C)** — experiment 01을 *로컬 VLA eval/서빙 오픈소스 도구*(consumer GPU·Windows/WSL2,
  세그폴트·의존성 해법 내장)로 productize **+** 2번째 정책을 동일 벤치(LIBERO)로 비교(ADR 0001 실측).
- [x] **Track A 도구화** — server/client/run.py 정제, `--policy/--suite/--ckpt` 파라미터화, requirements.txt+setup.sh, 유저 README/EXPERIMENT.md 분리, legacy/ 정리. 스모크 PASS (`2437688`).
- [x] **Track C 조사 게이트** — 2번째 정책 = **π0.5(openpi) GO**(LIBERO ckpt `pi05_libero` 공개), ACT는 NO-GO(LIBERO ckpt 없음 → M6 이전). 결정 박제: [ADR 0002](docs/adr/0002-act-deferred-to-m6.md)·[0003](docs/adr/0003-second-policy-separate-harness.md) (`04b3910`).
- [x] **C 설치 스모크** — openpi PyTorch가 Blackwell(sm_120)에서 **torch cu128 오버라이드**로 동작 확인(핀 cu126는 실패). `~/openpi` venv 구축 완료.
- [x] **C 본작업** — π0.5(openpi) libero_spatial 실측 → [experiment 02](experiments/02-action-repr-bench/README.md). **full-suite n=500 대칭·공식: π0.5 98.4%(492/500) vs OpenVLA 77.4%(387/500), +21pp, Fisher p=1.4e-27, CI 비겹침**. (초안 matched 3task → 2026-06-11 OpenVLA 10task×50 재측정 + 공식 JAX 변환으로 표본비대칭·provenance 두 caveat 해소.) ADR 0001 실측 보강. ⚠ JAX gsutil 9p 실패→WSL 순수-python GCS(gcsfs)로 우회 변환, torch cu128 직접호출.
- 완료 기준: 남이 클론 → 1커맨드로 VLA 평가 재현(Track A) + 2모델 결과표(Track C) ✅

### M5 — 포트폴리오 패키징 (legibility) ✅
- [x] public `README.md` 재설계 — 포트폴리오 랜딩(5분에 "뭐 알고/뭐 만들었나") (`f0d58ba`)
- [x] askewly 블로그 서사 글 1편 — "논문은 안다고 착각하게 만듭니다" 라이브 발행(`dcebaf8`+KV 시드)
- [x] vault 정리 — synthesis 노트 1개 + Research 00-INDEX physical-ai 섹션 등록
- 완료 기준: README 랜딩 + 블로그 글 발행 ✅

### M6 — 디지털 트윈 (sim, 하드웨어 불필요) ✅
> SO-100 팔을 sim에 세우고 정책 롤아웃을 웹에서 인터랙티브 3D로 보여준다. 하드웨어 없이 sim→real 직전까지.
> M5에서 분리·전진 배치(2026-06-12) — M6를 하드웨어 게이트(구 M6, 현 M7)에서 떼어내 *지금 착수 가능*하게.
- 스택 선택: [ADR 0004](docs/adr/0004-digital-twin-stack.md) — SO-100 MJCF(공식 SO-ARM100) + MuJoCo WASM 웹 replay, 정책은 replay-first.
- [x] **SO-100 모델 확보** — Menagerie `trs_so_arm100`(메인 정식 포함 확인) 로드 + 오프스크린 렌더(Windows GL) → [experiment 03](experiments/03-digital-twin/README.md). 스모크 PASS, FK·액추에이션 확인.
- [x] **sim 태스크 + 롤아웃 replay** — sweep → **scripted pick-and-place 3단 스택**(`make_pick_trajectory.py`: Jacobian IK 웨이포인트 + 집기 순간 weld carry, qpos 385프레임 기록). 데스크탑·웹 모두 운동학 재생(mp4==웹). 학습 정책(ACT sim-학습)은 M7 실물 직결로 후속([ADR 0002](docs/adr/0002-act-deferred-to-m6.md)).
- [x] **웹 인터랙티브 3D 트윈** — mujoco_wasm(공식 DeepMind WASM)로 브라우저 트윈 → [experiments/03-digital-twin/web](experiments/03-digital-twin/web/README.md). 자동재생 replay 루프 + interactive 토글·반응형(QHD/노트북/모바일), 콘솔 에러 0. **라이브: https://physical-ai-arm.askewly.com** (Vercel 순수 정적 CDN, askewly.com 서브도메인).
- 완료 기준: 브라우저에서 도는 인터랙티브 SO-100 트윈 ✅ + 공개 호스팅 ✅ + 정책 롤아웃 replay ✅

### M8 — 학습 정책 sandbox (sim, 하드웨어 불필요) ✅
> 저가팔 구매(M7)가 비현실적 → 하드웨어 게이트 우회. 트윈을 "SO-100 외에도 다양한 피지컬 AI를
> 실험하는 sandbox"로 깎고, 재생기에서 **브라우저에서 도는 학습된 정책**으로 격상. [ADR 0005](docs/adr/0005-learned-policy-sandbox.md).
- [x] **하네스 일반화 (1단계)** — SO-100 하드코딩 파이프라인을 `experiments.json` config-driven 하네스로(`harness.py` + 범용 물리 레코더). humanoid를 bespoke 0줄로 통과시켜 일반성 실증 (`0ecb94f`).
- [x] **축 설계 박제** — A+B 결합(임베디먼트 갤러리 + 직접 학습 정책), 파일럿=Go1 보행, [ADR 0005](docs/adr/0005-learned-policy-sandbox.md) (`b98198c`).
- [x] **Phase 1 학습 spike** — Playground Go1 joystick PPO 200M steps **8.8분**(RTX5090, jax 0.9.2) → 손작성 ONNX(parity 4.8e-6) → native mujoco 보행 12s·11.8m·0.99m/s. [experiment 04](experiments/04-go1-rl-walk/README.md) (`66f7ff5`).
- [x] **Phase 2 데스크탑 통합** — go1 씬 self-contained 번들 + `policy` 블록 + `rollout_policy.py`(closed-loop). 번들 씬 obs parity 0.0 + 보행 mp4 (`5f74ead`).
- [x] **Phase 3 웹 live closed-loop** — `onnxruntime-web` 브라우저 추론(obs→onnx→ctrl→mj_step@50Hz). JS obs builder byte-parity 0.0, 카메라 추적. **라이브 `?exp=go1-walk` 보행 7.84m + 0 콘솔에러** (`c535311`).
- [x] **후속 다듬기 (2026-06-14)** — go1 메시 깨짐 수정 + **자동 시각 QA 하네스**(qaStep+playwright, Claude가 라이브 자가검증) + command 조이스틱 슬라이더 + 배포 무캡(SHA 업로드) + **Shadow Hand 갤러리 추가**(축 A 폭). 라이브 4종(팔·사족+정책·휴머노이드·손) QA PASS. Spot·Panda·G1은 별도 세션 보류.
- 완료 기준: 라이브에서 직접 학습한 정책이 실시간으로 Go1을 걷게 한다 + 0 콘솔 에러. ✅ **달성** — https://physical-ai-arm.askewly.com/?exp=go1-walk

### M7 — 실물 도달 (하드웨어 게이트, 보류) ⬜
- [ ] SO-100류 저가 로봇팔(~$200-400) 구매·조립
- [ ] teleoperation 데이터 수집 → ACT 모방학습 → sim→real 이식, 1개 태스크 수행
- 완료 기준: 실물 팔 태스크 수행 영상 + reality gap 회고. ※ 저가팔 구매 시 착수 (현재 보류, M8 우선)

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

## 의사결정 이력
"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 *의도적 제외*는 `docs/adr/`에 ADR로.
