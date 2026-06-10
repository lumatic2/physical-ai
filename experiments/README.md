# experiments/

손으로 직접 짜보는 작은 구현들. 각 실험은 `<NN>-<slug>/README.md` 4섹션 형식 —
템플릿: [EXPERIMENT_TEMPLATE.md](EXPERIMENT_TEMPLATE.md).

## 인덱스

| # | 슬러그 | 가설 (한 줄) | 결과 |
|---|--------|-------------|------|
| 01 | [vla-local-eval](01-vla-local-eval/README.md) | RTX 5090서 OpenVLA 7B REST 추론 → LIBERO success rate > 0 | ✅ H1 15.1GB · H2 168ms · H3 73%(11/15) |
| 02 | [action-repr-bench](02-action-repr-bench/README.md) | 같은 libero_spatial서 π0.5(flow-matching chunk)가 OpenVLA(이산토큰)와 비교 가능한 SR | ✅ π0.5 **97.6%**(488/500) vs OpenVLA 73%(11/15) — H1·H2 PASS |

## 실행 원칙
- mock 먼저, real 다음 (비용·시간 절약 + 가설 격리)
- `verify/` 폴더에 raw 출력 박제 (재현성)
- 통찰 섹션 비면 실험이 안 끝난 것
