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

> ✅ M1~M4 전부 완료. 모든 가설(H1·H2·H3) PASS.

### 데이터
| Run | 단계 | VRAM (GB) | latency p50/p95 (ms) | success rate | 비고 |
|-----|------|-----------|----------------------|--------------|------|
| M1  | mock REST round-trip | — | — | — | ✅ PASS: status 200, action ndarray (7,), json-numpy round-trip 무손실 (`verify/m1-client.log`) |
| M2  | real 로딩 (VRAM) | 15.13 | — | — | ✅ openvla-7b sdpa/bf16, OOM 없음, load 176.6s (`verify/m2-load.json`). torchvision ABI·transformers 5.x 마찰 해소 후 |
| M3  | real 추론 latency | 15.13 | 168.1 / 171.5 | — | ✅ unnorm_key=bridge_orig, action (7,) 실값 산출 (`verify/m3-latency.json`) |
| M4  | LIBERO success | 15.13 | — | **73.3% (11/15)** | ✅ libero_spatial 3 task×5 trial, REST 서버/클라 분리로 세그폴트 해소 (`verify/m4-eval.json`). OpenVLA 보고 84.7±0.9%(n=1500) 대비 작은 표본(n=15) directionally 일치 |

### 박제 위치
- `verify/` 폴더에 raw 출력 보존 (서버 로그·nvidia-smi·latency 측정 stdout·LIBERO rollout 로그)

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- RTX 5090 단일 GPU에서 OpenVLA 7B는 **15.13GB**로 적재(여유 충분), sdpa로 추론 **p50 168ms** — 실시간 제어 루프에 충분.
- LIBERO-spatial(finetuned ckpt)에서 **11/15=73.3% success** — 모델이 실제 manipulation 수행(3 태스크 4/3/4로 고름).
- **핵심 발견 — model↔sim 프로세스 분리는 워크어라운드가 아니라 정석**: `import tensorflow` 한 프로세스에서 robosuite EGL 컨텍스트 생성이 세그폴트(`torch`는 안전, 격리 테스트로 확정). 모델+시뮬을 한 프로세스에 넣으면 충돌하는데, **deploy.py REST 서버/클라이언트 분리**(모델=서버, 시뮬=클라)가 이 충돌의 구조적 해법이자 experiment #1의 본래 설계 — `/act` REST 계약이 #4 실물 로봇 구동의 SW 골격과 동일함을 실증.
- **환경 마찰 체인(전부 박제)**: ① torchvision cu128 ABI 불일치 ② transformers 5.x에 `AutoModelForVision2Seq` 제거→4.40.1 핀 ③ torch 2.6+ `weights_only=True`가 LIBERO `.pruned_init` 차단 ④ LIBERO `--no-deps`로 stale 핀 회피 ⑤ json_numpy 전역 patch가 lib json 파싱 깸→경계 명시 인코딩 ⑥ json_numpy read-only 배열→copy. WSL2 + Blackwell(sm_120) + 2024년 OpenVLA 스택의 시간차 마찰.

### 가설은 통과했나?
- [x] **H1 (VRAM 적재) — PASS**: 15.13GB << 32GB, OOM 없음 (`verify/m2-load.json`)
- [x] **H2 (latency) — PASS**: p50 168ms / p95 172ms << 500ms (`verify/m3-latency.json`)
- [x] **H3 (success rate) — PASS**: 73.3%(11/15) >> 0; OpenVLA 보고 84.7±0.9%(n=1500, README:511) 대비 작은 표본(n=15·3/10 task·single seed·sdpa) directionally 일치 (`verify/m4-eval.json`)

### 정의에 반영
- m3-ideas #1 권장 시퀀스 검증됨 — `deploy.py` REST `/act` 패턴이 이후 #2·#3·#5·#4의 SW 계약으로 재사용 가능.
- **ADR 후보**: "로컬 VLA 평가는 model(서버)↔sim(클라) 프로세스 분리" — tf↔EGL in-process 충돌의 구조적 회피이자 서빙 정석. 별도 reference 더 모이면 ADR 발행 검토.

### 다음 실험 후보
- 전체 10 task × 50 trial × 3 seed로 OpenVLA 보고치(84.7%) 재현 (시간 큼, ~수 시간)
- flash-attn 빌드해 sdpa 대비 latency·success 차이 측정 (Blackwell flash-attn 빌드 가능 여부도 검증 대상)
- #2 (π0·ACT 추가 → ADR 0001 동작표현 3축 실측) 또는 #5 (play 데모, 가벼움)
