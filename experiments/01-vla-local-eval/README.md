# 01-vla-local-eval — VLA 로컬 추론 서버 + 시뮬 평가

> `experiments/01-vla-local-eval/README.md` — 실험은 *가설·방법·결과·통찰* 4섹션.
> 통찰이 비었으면 실험이 *안 끝난* 것. mock + real 둘 다 박제 권장.
> 뿌리: `docs/m3-ideas.md` 후보 #1. 실행 환경: **WSL2 (Ubuntu-24.04) + RTX 5090 32GB** (2026-06-09 확정).

## 1. 가설 (Hypothesis)

RTX 5090(32GB) 단일 GPU에서 OpenVLA 7B를 `deploy.py` REST 서버(`/act`)로 띄우면:

- **(H1)** 7B + flash-attention-2 + bf16 가중치가 32GB VRAM 안에 적재된다 (OOM 없이).
- **(H2)** `/act` 단일 추론 latency가 실시간 제어 루프에 쓸 만한 범위(p50 < 500 ms)에 든다.
- **(H3)** LIBERO 시뮬 벤치(예: `libero_spatial` 일부 태스크)에서 success rate가 0%보다 유의하게 높다 (모델이 실제로 의미 있는 동작을 낸다).

세 가설은 각각 반증 가능: OOM이면 H1 FAIL, latency가 초 단위면 H2 FAIL, success rate 0이면 H3 FAIL.

## 2. 방법 (Method)

### 셋업
- **모델**: mock 단계 = stub(고정 7-dim action 반환) / real 단계 = `openvla/openvla-7b` (HF Hub, ~14GB)
- **데이터**: mock = 더미 이미지 `np.zeros((256,256,3), uint8)` / real = LIBERO 시뮬 관측 프레임
- **하네스 구성**:
  - 서버 deps: `uvicorn fastapi json-numpy` (+ real: `torch transformers flash-attn draccus`)
  - 클라이언트 deps: `requests json-numpy numpy`
  - REST 계약 (OpenVLA `deploy.py:65-123`, 접근 2026-06-09):
    `POST /act` ← `{"image": ndarray, "instruction": str, "unnorm_key": Optional[str]}` → `{"action": ndarray}`

### 시나리오 (mock 먼저, real 다음)
- **M1 (mock)**: 자체 stub `/act` 서버 + 클라이언트로 REST round-trip 검증. json-numpy 직렬화로 ndarray 왕복이 깨지지 않는지, 7-dim action 벡터가 돌아오는지 확인. — *환경 마찰(서버 기동·포트·직렬화)을 모델 로딩과 격리*.
- **M2 (real-load)**: 실제 `openvla/openvla-7b` 로딩만. VRAM 사용량 측정 (H1). 시뮬 없음.
- **M3 (real-infer)**: 단일 더미 이미지로 실제 `/act` 추론 1회 + 반복 측정 → latency p50/p95 (H2).
- **M4 (real-sim)**: LIBERO 시뮬 연결, N개 태스크 rollout → success rate (H3).

### 측정 metric
- VRAM 사용량 (GB, `nvidia-smi`) — H1
- `/act` latency (ms, p50/p95, N회 반복) — H2
- LIBERO success rate (%, 태스크 수 명시) — H3
- 각 단계 환경 마찰 로그 (의존성 설치 실패·CUDA 버전 충돌 등) — 정성

## 3. 결과 (Results)

> 🔄 M1 완료 / M2~M4 미실행.

### 데이터
| Run | 단계 | VRAM (GB) | latency p50/p95 (ms) | success rate | 비고 |
|-----|------|-----------|----------------------|--------------|------|
| M1  | mock REST round-trip | — | — | — | ✅ PASS: status 200, action ndarray (7,), json-numpy round-trip 무손실 (`verify/m1-client.log`) |
| M2  | real 로딩 (VRAM) | | — | — | |
| M3  | real 추론 latency | | | — | |
| M4  | LIBERO success | | | | |

### 박제 위치
- `verify/` 폴더에 raw 출력 보존 (서버 로그·nvidia-smi·latency 측정 stdout·LIBERO rollout 로그)

## 4. 통찰 (Insights)

> ⬜ 미작성. Judge 규약: §3 결과가 박제되기 전 이 섹션 작성 금지.

### 무엇을 알아냈나
- (run 후)

### 가설은 통과했나?
- [ ] H1 (VRAM 적재) — PASS/FAIL + 근거
- [ ] H2 (latency) — PASS/FAIL + 근거
- [ ] H3 (success rate) — PASS/FAIL + 근거

### 정의에 반영
- (해당 시 `docs/adr/` 또는 정의 파일에 반영)

### 다음 실험 후보
- (여기서 발견한 새 질문)
