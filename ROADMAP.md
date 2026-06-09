# ROADMAP

> 이 학습/리서치 레포의 마일스톤·완료 이력. PRD 가 *무엇을 만들지*라면, ROADMAP 은 *무엇을 알아낼지*.

## 왜 이 레포

피지컬 AI(embodied AI·로보틱스)가 2026~2027년 더 핫해질 것으로 보고, ① 관련 지식을 논문·문헌 기반으로 공부해 축적하고, ② 그 지식을 피지컬 AI에 들어갈 **소프트웨어 또는 실물 제작 프로젝트 아이디어**로 발전시키기 위한 레포.

지식은 `docs/` 에 차곡차곡 정리하고 `~/vault/` 로 이전해 장기 자료집으로 만든다.

## 학습 목표

1분 안에 — **피지컬 AI가 무엇이고, 핵심 기술 스택(인지·정책·시뮬·하드웨어)과 주요 플레이어가 누구이며, 내가 무엇을 만들 수 있는지** — 를 설명할 수 있다.

## 마일스톤

### M1 — 지형 파악 (landscape & 정의) ✅
- [x] 피지컬 AI 핵심 용어·taxonomy 정리 (embodied AI / VLA / world model / sim-to-real / manipulation / locomotion 등)
- [x] 주요 플레이어·랩 맵 (NVIDIA Isaac·GR00T, Physical Intelligence, Figure, 1X, Google DeepMind Gemini Robotics, Tesla Optimus 등)
- [x] 읽을 핵심 논문·문헌 reading list 10~15개 수집 → `docs/landscape.md` §4 (15개)
- 완료 기준: `docs/landscape.md` 에 용어·플레이어·reading list 한 장으로 정리 완료 ✅ (2026-06-09)

### M2 — 레퍼런스 정독 (deep dive) 🔄
- [x] reading list 중 핵심 5개를 `references/` 에 분석 (5섹션) — OpenVLA·π0·ACT·OXE·VLA서베이
- [x] 동작 표현 대비를 ADR로 박제 → [ADR 0001](docs/adr/0001-vla-action-representation.md)
- [ ] 정리한 지식을 `docs/` 주제별 노트로 승격 (landscape §2 정의 갱신 후보)
- [ ] `~/vault/` 로 이전해 자료집화 (`/vault-write`)
- 완료 기준: 5개 reference 5섹션 완성 + vault 이전 완료 (정독 5/5 완료, vault 이전 미완)

### M3 — 프로젝트 아이디어 → 작은 구현
- [ ] 축적한 지식 기반으로 만들 수 있는 프로젝트 아이디어 3~5개 발굴 (소프트웨어/실물)
- [ ] 1개 선정 후 최소 프로토타입 또는 실험 (`experiments/` EXPERIMENT_TEMPLATE)
- 완료 기준: 아이디어 목록 문서화 + 선정 1개의 실험 결과 기록

## 완료 이력
- 2026-06-09 — M1 지형 파악 완료. `docs/landscape.md` 작성 (정의·용어 11종·4레이어 스택·플레이어 맵 SW/HW/시뮬·reading list 15개).

## 의사결정 이력
"왜 X 안 봄?", "왜 Y 갈래로 안 감?" 같은 *의도적 제외*는 `docs/adr/` 에 ADR 로.
