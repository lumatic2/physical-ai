# ROADMAP

> 이 레포의 마일스톤·완료 이력. **포트폴리오 모드** — 완료 기준은 "내가 이해했다"(내부)가 아니라
> "남이 5분 보고 납득한다"(외부). 마일스톤마다 보여줄 수 있는 산출물(showable artifact)이 나온다.
> 마지막 업데이트: 2026-06-12

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
| M6 | 디지털 트윈 (sim) | 하드웨어 없이 sim→real 직전까지, 웹에서 보여준다 | 인터랙티브 3D 트윈 [라이브](https://physical-ai-arm.askewly.com) + 정책 롤아웃 | 🔄 |
| M7 | 실물 도달 (다음 분기) | sim→real 한 바퀴, 실물까지 만든다 | SO-100 저가팔 + ACT, 수행 영상 | ⬜ |

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

### M6 — 디지털 트윈 (sim, 하드웨어 불필요) ⬜
> SO-100 팔을 sim에 세우고 정책 롤아웃을 웹에서 인터랙티브 3D로 보여준다. 하드웨어 없이 sim→real 직전까지.
> M5에서 분리·전진 배치(2026-06-12) — M6를 하드웨어 게이트(구 M6, 현 M7)에서 떼어내 *지금 착수 가능*하게.
- 스택 선택: [ADR 0004](docs/adr/0004-digital-twin-stack.md) — SO-100 MJCF(공식 SO-ARM100) + MuJoCo WASM 웹 replay, 정책은 replay-first.
- [x] **SO-100 모델 확보** — Menagerie `trs_so_arm100`(메인 정식 포함 확인) 로드 + 오프스크린 렌더(Windows GL) → [experiment 03](experiments/03-digital-twin/README.md). 스모크 PASS(nq=6, FK, 액추에이션), 트윈 sweep 영상 산출.
- [ ] **sim 태스크 + 롤아웃** — 현재 sweep(replay-first)까지. 실제 정책 롤아웃 replay / ACT sim-학습은 후속(M7 실물 직결, [ADR 0002](docs/adr/0002-act-deferred-to-m6.md)); 기존 VLA는 액션 차원이 SO-100과 불일치
- [x] **웹 인터랙티브 3D 트윈** — mujoco_wasm(공식 DeepMind WASM)로 브라우저 인터랙티브 트윈 → [experiments/03-digital-twin/web](experiments/03-digital-twin/web/README.md). 홈 포즈 직립·관절 라이브 구동·반응형(QHD/노트북/모바일), 콘솔 에러 0. **라이브: https://physical-ai-arm.askewly.com** (Vercel 순수 정적 CDN, askewly.com 서브도메인).
- 완료 기준: 브라우저에서 도는 인터랙티브 SO-100 트윈 ✅ + 공개 호스팅 ✅ (정책 롤아웃 replay만 후속)

### M7 — 실물 도달 (다음 분기, 하드웨어 게이트) ⬜
- [ ] SO-100류 저가 로봇팔(~$200-400) 구매·조립
- [ ] teleoperation 데이터 수집 → ACT 모방학습 → sim→real 이식, 1개 태스크 수행
- 완료 기준: 실물 팔 태스크 수행 영상 + reality gap 회고. ※ M6 트윈 완주 후 착수

## 완료 이력
- 2026-06-09 — M1 지형 파악. `docs/landscape.md`(정의·용어 11종·4레이어 스택·플레이어 맵·reading list 15개).
- 2026-06-09 — M2 레퍼런스 정독. 5편 5섹션 분석 + ADR 0001 동작표현 3축 + vault 이전.
- 2026-06-09 — M3 첫 실험. `experiments/01` VLA 로컬 추론 + LIBERO 평가, H1·H2·H3 PASS(success 73%), tf↔EGL 세그폴트를 REST 서버/클라 분리로 해소, 마찰 6건 박제. **로드맵을 포트폴리오 모드로 재설계(M4~M6 추가).**
- 2026-06-11 — **M4 완주**. Track A(experiment 01 도구화) + Track C(π0.5 비교, experiment 02). 동작표현 2축 실측: matched 3 task에서 flow-matching(π0.5) 98.7% vs 이산토큰(OpenVLA) 73.3%, Fisher p<1e-3. openpi 비-Docker(서버 cu128 / 클라 py3.8 별도 venv), JAX 다운 9p 실패→HF 포트 fallback. Codex adversarial-review가 task-모집단 과장(10 vs 3) 잡아내 matched-subset으로 교정 후 push.
- 2026-06-11 (후속) — **M4 잔여 caveat 2건 해소**. ① setup.sh 클린룸 검증(빈 venv) — requirements 누락 의존 2건(accelerate·LIBERO런타임) 잡아 보정(`a9823dd`). ② full apples-to-apples 재측정: OpenVLA 10task×50=500ep(77.4%) + 공식 JAX `pi05_libero` 변환(WSL 순수-python GCS로 9p 우회)으로 π0.5 공식 500ep(98.4%). **대칭·공식 head-to-head: +21pp, Fisher p=1.4e-27, CI 비겹침**. 초안 matched OpenVLA 73.3%(11/15)는 소표본 과소추정이었음(n=150→89.3%)을 정직 교정.
- 2026-06-11 (후속) — **M5 완주**. ① public README 포트폴리오 랜딩 재설계(`f0d58ba`). ② askewly 블로그 글 "논문은 안다고 착각하게 만듭니다" anti-AI verify PASS → 라이브 발행(`dcebaf8`+KV). ③ vault: M2~M4 통합 synthesis 노트 작성 + Research 00-INDEX에 physical-ai 섹션 등록(고립 해소). 남은 건 M6(실물 로봇팔).
- 2026-06-12 — **M6 대부분 완주**(정책 replay만 남음). M6를 하드웨어 게이트에서 분리(M6 디지털 트윈 / M7 실물), [ADR 0004](docs/adr/0004-digital-twin-stack.md) 스택 결정. SO-100(Menagerie `trs_so_arm100`, 메인 머지 확인) MuJoCo 로드 스모크 PASS → 오프스크린 렌더 mp4 → `experiments/03-digital-twin`. **웹 인터랙티브 3D**: zalo/mujoco_wasm(공식 DeepMind WASM) 기반 자체완결 정적 앱 `web/`, 홈 키프레임 직립·반응형. Vercel 배포 중 node_modules 미서빙 함정 → deps CDN화로 순수정적 해소. **커스텀 도메인 라이브: physical-ai-arm.askewly.com**(CF_DNS_TOKEN으로 CNAME). askewly.com Products에 트윈 카드+robot-arm 아이콘 추가(자동배포). 커밋 `4628bfc`·`84f3fa2`·`704e8ed`·`f66d0a0`.

## 의사결정 이력
"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 *의도적 제외*는 `docs/adr/`에 ADR로.
