# ROADMAP

> 이 레포의 마일스톤·완료 이력. **포트폴리오 모드** — 완료 기준은 "내가 이해했다"(내부)가 아니라
> "남이 5분 보고 납득한다"(외부). 마일스톤마다 보여줄 수 있는 산출물(showable artifact)이 나온다.
> 마지막 업데이트: 2026-06-10

## 왜 이 레포 (포트폴리오 thesis)

피지컬 AI(embodied AI·로보틱스) 기초 지식을 **입증하는 포트폴리오**.

한 문장: *"피지컬 AI 기초 지식이 있고(지형·이론) → 이론을 내 손으로 직접 실험으로 돌렸고(hands-on)
→ 쓸만한 SW를 만들었다(→ 다음 단계 실물)."*

피지컬 AI가 2026~2027 더 핫해질 것으로 보고, ① 논문·문헌 기반 지식 축적(`docs/` → `~/vault/`)에서
출발해 ② 직접 돌린 실험과 쓸만한 SW(나아가 실물)로 입증한다.

노출: GitHub 레포 README(개발자·채용) · askewly 블로그 서사 글(통찰·판단) · `~/vault/`(장기 자료집).

## 마일스톤 (한눈에)

| # | 마일스톤 | 입증하는 것 | 산출물 (showable) | 상태 |
|---|---------|------------|-------------------|------|
| M1 | 지형 파악 | 분야 전체를 매핑한다 | `docs/landscape.md` | ✅ |
| M2 | 레퍼런스 정독 + ADR | 1차 문헌을 비판적으로 읽는다 | 5× `ANALYSIS.md`, ADR 0001 | ✅ |
| M3 | 첫 실험 (이론 직접 실행) | 논문 모델을 내 GPU에서 실행·평가한다 | `experiments/01` (H1·H2·H3 PASS, LIBERO 73%) | ✅ |
| M4 | 쓸만한 SW 승격 (flagship) | 실험을 남이 쓸 도구/데모로 만든다 | 클린 README + 1-command 재현 + 결과 | 🔄 |
| M5 | 포트폴리오 패키징 | 5분 안에 실력이 읽힌다 | public README + 블로그 글 1편 + vault 정리 | ⬜ |
| M6 | 실물 도달 (다음 분기) | sim→real 한 바퀴, 실물까지 만든다 | SO-100류 저가팔 + ACT, 수행 영상 | ⬜ |

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

### M4 — 쓸만한 SW로 승격 (flagship) 🔄
- **flagship (채택: A+C)** — experiment 01을 *로컬 VLA eval/서빙 오픈소스 도구*(consumer GPU·Windows/WSL2,
  세그폴트·의존성 해법 내장)로 productize **+** 2번째 정책을 동일 벤치(LIBERO)로 비교(ADR 0001 실측).
- [x] **Track A 도구화** — server/client/run.py 정제, `--policy/--suite/--ckpt` 파라미터화, requirements.txt+setup.sh, 유저 README/EXPERIMENT.md 분리, legacy/ 정리. 스모크 PASS (`2437688`).
- [x] **Track C 조사 게이트** — 2번째 정책 = **π0.5(openpi) GO**(LIBERO ckpt `pi05_libero` 공개), ACT는 NO-GO(LIBERO ckpt 없음 → M6 이전). 결정 박제: [ADR 0002](docs/adr/0002-act-deferred-to-m6.md)·[0003](docs/adr/0003-second-policy-separate-harness.md) (`04b3910`).
- [x] **C 설치 스모크** — openpi PyTorch가 Blackwell(sm_120)에서 **torch cu128 오버라이드**로 동작 확인(핀 cu126는 실패). `~/openpi` venv 구축 완료.
- [ ] 🔄 **C 본작업** — pi05_libero 다운+변환 → openpi 하네스로 libero_spatial 평가 → 비교표(OpenVLA 73% vs π0.5) + ADR 0001 실측 갱신
- 완료 기준: 남이 클론 → 1커맨드로 VLA 평가 재현 + 최소 2모델 결과표

### M5 — 포트폴리오 패키징 (legibility) ⬜
- [ ] public `README.md` 재설계 — 포트폴리오 랜딩(5분에 "뭐 알고/뭐 만들었나" 전달). ※ 현재 루트 CLAUDE.md/ROADMAP은 내부용(gitignored)
- [ ] askewly 블로그 서사 글 1편 (M3·M4 여정·통찰)
- [ ] vault 정리 (장기 자료집)
- 완료 기준: README 랜딩 + 블로그 글 발행

### M6 — 실물 도달 (다음 분기) ⬜
- [ ] SO-100류 저가 로봇팔(~$200-400) 구매·조립
- [ ] ACT 모방학습 sim→real, 1개 태스크 수행
- 완료 기준: 실물 팔 태스크 수행 영상 + 회고. ※ M4·M5 완주 후 착수

## 완료 이력
- 2026-06-09 — M1 지형 파악. `docs/landscape.md`(정의·용어 11종·4레이어 스택·플레이어 맵·reading list 15개).
- 2026-06-09 — M2 레퍼런스 정독. 5편 5섹션 분석 + ADR 0001 동작표현 3축 + vault 이전.
- 2026-06-09 — M3 첫 실험. `experiments/01` VLA 로컬 추론 + LIBERO 평가, H1·H2·H3 PASS(success 73%), tf↔EGL 세그폴트를 REST 서버/클라 분리로 해소, 마찰 6건 박제. **로드맵을 포트폴리오 모드로 재설계(M4~M6 추가).**

## 의사결정 이력
"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 *의도적 제외*는 `docs/adr/`에 ADR로.
