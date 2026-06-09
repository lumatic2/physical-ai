# Physical-Intelligence/openpi (π0) 분석

> 시간 박스 90분. 클론: https://github.com/Physical-Intelligence/openpi (2026-06-09 접근). 논문: [arXiv 2410.24164](https://arxiv.org/abs/2410.24164).

## 1. 한 줄 요약 / 무엇을 하는 하네스인가

**flow matching 기반 generalist VLA** — PaliGemma(Gemma LLM + SigLIP 비전) VLM 위에 별도 **action expert** 트랜스포머를 붙이고, 동작을 *토큰화하지 않고* flow matching(확산 변형)으로 연속 생성. OpenVLA가 "동작=언어 토큰"이라면 π0는 "동작=노이즈에서 적분으로 복원하는 연속 벡터". JAX/Flax 구현. 분류 어휘로는 **L1 정책 모델(연속 제어)** + **L2 다중 로봇 정책 어댑터(aloha/droid/ur5/libero)** + **L3 websocket 추론 서버**.

## 2. 디렉터리 지도 (핵심 폴더만)

```
openpi/
├── src/openpi/
│   ├── models/
│   │   ├── pi0.py            # ★ flow matching 코어 (compute_loss / sample_actions)
│   │   ├── pi0_fast.py       # FAST 토큰화 변형 (autoregressive 대안)
│   │   ├── gemma.py / siglip.py / vit.py  # PaliGemma 백본 구성요소
│   │   └── tokenizer.py      # 언어 프롬프트 토크나이저
│   ├── policies/             # 로봇별 입출력 어댑터 (aloha/droid/libero/ur5)
│   ├── training/             # config·data_loader·RLDS dataset·optimizer
│   └── serving/websocket_policy_server.py  # ★ 추론 서버 (OpenVLA의 REST와 대비)
├── examples/                 # aloha_real/sim·droid·libero·ur5 실행 예제
└── packages/openpi-client/   # 경량 클라이언트 (로봇 측)
```

## 3. 아키텍처 레이어 매핑 (로보틱스 — landscape §2 4레이어와 정렬)

| 레이어 | 위치 (파일:줄) | 내용 |
|--------|---------------|------|
| 입력·센서 (관측) | `pi0.py:113-137` (embed_prefix) | 여러 카메라 이미지 + 언어 프롬프트를 prefix 토큰으로 임베딩 |
| 인지·추론 (VLM 백본) | `pi0.py:70-91` | PaliGemma(SigLIP So400m + Gemma) — prefix는 bidirectional attention |
| 정책·액션 생성 | `pi0.py:188-279` | **flow matching**: action expert(별도 Gemma) + `action_in_proj`/`action_out_proj`(연속) |
| 학습·데이터 | `pi0.py:189-214` (compute_loss), `training/droid_rlds_dataset.py` | velocity 예측 MSE 손실; RLDS 데이터 |
| 하드웨어·배포 | `serving/websocket_policy_server.py`, `policies/aloha_policy.py` 등 | websocket 서버 + 로봇별 정책 어댑터 |

## 4. 인상 깊은 코드/패턴 (파일 경로 + 줄 번호 필수)

- `src/openpi/models/pi0.py:195-214` — flow matching 학습: 노이즈와 정답 동작을 `x_t = t·noise + (1-t)·actions`로 보간하고, 목표 velocity `u_t = noise - actions`를 회귀(MSE). 카테고리 토큰 예측이 아닌 **연속 벡터장 학습**. OpenVLA의 256-bin 분류와 정반대 접근.
- `src/openpi/models/pi0.py:216-279` — `sample_actions`: 순수 노이즈에서 시작해 `num_steps=10` Euler 적분(`x_t + dt·v_t`)으로 동작 청크를 복원. 추론이 **반복적**(10 forward) — OpenVLA의 단일 generate와 비용 구조가 다름.
- `src/openpi/models/pi0.py:73-91` — LLM(PaliGemma)과 **action expert**(두 번째 Gemma config)를 한 모듈에 결합. 동작 생성을 LLM 헤드 재사용이 아니라 *전용 전문가*에 위임 — 표현력↑.
- `src/openpi/models/pi0.py:233-237` — prefix(이미지+언어) KV cache를 한 번 계산해 10번의 flow step에서 재사용. 반복 추론의 비용을 줄이는 실전 최적화.
- `src/openpi/models/pi0.py:69,162-169` — `pi05` 플래그로 π0.5의 adaRMS time conditioning 분기. 한 코드베이스에서 모델 세대 차이를 플래그로 관리.

## 5. 내 정의에 어떻게 반영할 것인가

- **동작 표현의 2대 패러다임 확정**: OpenVLA(이산 토큰화·단일 autoregressive) ↔ π0(연속 flow matching·반복 적분). 같은 "VLA"라도 정책 레이어 내부가 갈린다. landscape §2 "diffusion/flow-matching policy" 항목의 구체 실체.
- **백본은 수렴, 헤드는 분기**: 둘 다 VLM 백본(Prismatic vs PaliGemma)을 쓰지만, OpenVLA는 LLM 헤드 재사용 / π0는 전용 action expert. "어디서 동작을 만드는가"가 설계 분기점.
- **비용 트레이드오프**: π0는 표현력(연속·멀티모달 동작 분포)을 얻는 대신 추론이 N-step. M3에서 실시간 제어 주파수 고려 시 중요.
- 관련 ADR: `docs/adr/0001-vla-action-representation.md` (이번 M2에서 작성 — 토큰화 vs flow matching vs 직접 회귀(ACT) 3자 비교)

---

## 메타
- 수집일: 2026-06-09
- 논문/링크: [arXiv 2410.24164](https://arxiv.org/abs/2410.24164) · [pi.website/blog/pi0](https://www.pi.website/blog/pi0)
- 소요 시간: ~50분
- 다음에 볼 레포 후보: pi0_fast (FAST autoregressive 변형), big_vision(PaliGemma 원류)
