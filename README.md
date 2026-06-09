# physical-ai

> 피지컬 AI(embodied AI · 로보틱스) 학습·리서치 레포. 관련 지식을 논문·코드 수준으로 정독해 축적하고, 그 위에서 만들 프로젝트 아이디어를 발굴한다.

## 왜 이 레포

피지컬 AI가 2026~2027년 더 핫해질 것으로 보고, ① 지식을 체계적으로 공부해 자료집으로 쌓고, ② 그 지식을 **소프트웨어/실물 제작 프로젝트**로 발전시키기 위한 개인 학습 레포. 정리한 지식은 `~/vault/` 로도 이전해 장기 보관한다.

## 진행 상태

| 마일스톤 | 상태 | 산출물 |
|---------|------|-------|
| **M1** 지형 파악 | ✅ | [docs/landscape.md](docs/landscape.md) — 정의·용어·4레이어 스택·플레이어 맵·reading list 15편 |
| **M2** 레퍼런스 정독 | ✅ | [references/](references/) 5편 5섹션 분석 + [ADR 0001](docs/adr/0001-vla-action-representation.md) |
| **M3** 아이디어 → 구현 | 🔄 | [docs/m3-ideas.md](docs/m3-ideas.md) — 후보 5개 (실험 미착수) |

상세 이력은 [ROADMAP.md](ROADMAP.md).

## 핵심 발견 (M2)

VLA(Vision-Language-Action) 모델은 백본이 VLM으로 수렴하지만 **동작 표현**에서 3갈래로 갈린다 — 이산 토큰화(OpenVLA) · flow matching(π0) · CVAE 직접 회귀(ACT). 이를 **2D 좌표(구조축 × 동작표현축)** 로 정의했다. → [ADR 0001](docs/adr/0001-vla-action-representation.md)

## 구조

```
physical-ai/
├── ROADMAP.md            # 학습 목표·마일스톤·완료 이력
├── docs/
│   ├── landscape.md      # 피지컬 AI 지형도 (M1)
│   ├── m3-ideas.md       # 프로젝트 아이디어 (M3)
│   └── adr/              # 의사결정 기록 (Michael Nygard 포맷)
├── references/           # 외부 레포·논문 정독 노트 (ANALYSIS.md 5섹션)
│   └── */ANALYSIS.md     #   ⚠ 클론 소스는 gitignored, 분석 노트만 추적
├── experiments/          # 실험 기록 (EXPERIMENT_TEMPLATE 4섹션)
└── notes/                # 자유 형식 리딩 메모
```

## 하네스

`harness-bootstrap`(learning 갈래)으로 부팅됨 — pre-commit hook + judge 규약(5섹션 다 채우기 전 통찰 보고 금지, 인용은 출처+접근일 필수). 작업 방식은 [CLAUDE.md](CLAUDE.md) 참조.

레퍼런스 정독·실험은 1 reference = 1 step 단위로 진행하며, 인덱스 표([references/README.md](references/README.md))가 status machine 역할을 한다.
