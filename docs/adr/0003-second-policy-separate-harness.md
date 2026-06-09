# 0003 — 2번째 정책(π0.5) 비교는 통합 /act 아닌 "별도 하네스 · 동일 벤치마크"

- Status: Accepted (2026-06-10)
- 근거 reference: Physical-Intelligence/openpi(#2), openvla/openvla(#1)
- 관련: [[0001-vla-action-representation]], [[0002-act-deferred-to-m6]], experiment 01(vla-local-eval) Track C

## Context

M4 Track A에서 experiment 01을 정책-파라미터화한 도구로 만들며 `server.load()`에 "2번째 정책 어댑터 드롭인" 시밍을 뒀다.
순진한 기대는 π0.5도 같은 REST `/act` 계약(이미지+instruction → 단일 7-dim action)에 어댑터 하나로 끼우는 것이었다.

Track C 조사 게이트(2026-06-10)에서 드러난 사실:

- **스택 격리 불가피** — openpi PyTorch π0.5는 `transformers==4.53.2` + **transformers 라이브러리 파일 수동 패치**를
  요구한다. OpenVLA 서버의 `transformers==4.40.1` 핀과 정면충돌하며, 패치는 uv 캐시를 전역 오염시킨다고 README가 경고한다
  (openpi `README.md` "PyTorch Support" §, 접근 2026-06-10). → π0.5는 **별도 venv·별도 프로세스**가 강제됨.
- **action grain 불일치** — π0.5는 flow-matching으로 action *horizon(chunk)*을 한 번에 생성한다. OpenVLA의 single-step
  autoregressive와 추론 단위가 다르다(ADR 0001). 단일-step `/act`에 욱여넣으면 chunk 큐잉을 서버가 숨겨야 해서 계약이 왜곡된다.
- **openpi가 이미 자기 하네스를 가짐** — `scripts/serve_policy.py`(정책 서버) + `examples/libero/main.py`(LIBERO 클라이언트)로
  policy-server 평가를 제공한다. 이는 experiment 01의 server/client 분리와 *동일 철학*이며, 우리 LIBERO 포크가 아닌
  openpi 자체 LIBERO(third_party/libero)로 검증된 경로다.

## Decision

**π0.5를 experiment 01의 통합 `/act` 하네스에 끼우지 않는다.** 대신 **"별도 하네스 · 동일 벤치마크 · 비교표"** 로 비교한다:

1. π0.5는 **openpi 자체 LIBERO eval 하네스**(별도 venv, serve_policy + main.py)로 돌려 success rate를 수집한다.
2. OpenVLA는 experiment 01 하네스로 돌린 기존 실측(73%, n=15)을 쓴다.
3. 비교의 *공정성*은 "같은 코드"가 아니라 **같은 벤치마크(LIBERO 동일 suite) + 명시된 프로토콜 차이**(표본 수·seed·전처리)로 확보한다.
4. ADR 0001의 "동작표현 실측 갱신"은 *동일 벤치마크 위 두 동작표현 비교*로 충족된 것으로 본다.

`server.load()`의 정책 분기 시밍은 **동일 스택·single-step 정책**(예: 다른 OpenVLA 변종)을 위한 자리로 남기고, π0.5처럼
스택·grain이 다른 정책은 별도 하네스로 둔다.

## Consequences

- **(+)** 스택 충돌(transformers 핀)·전역 캐시 오염 위험을 프로세스/venv 격리로 원천 차단. 두 도구가 서로를 깨지 않음.
- **(+)** action-chunk grain을 그대로 둠 — π0.5를 그 본래 추론 단위로 평가(왜곡 없는 실측).
- **(+)** 각 정책을 그 저자가 검증한 LIBERO 경로로 돌려 재현 신뢰도↑.
- **(−)** "클론→1커맨드로 N개 정책"이라는 단일 도구의 매끈함은 π0.5에 한해 깨짐 — 사용자는 openpi 별도 셋업이 필요.
  experiment 01 도구의 `--policy`는 당분간 동일-스택 정책에만 유효.
- **(−)** 비교표에 프로토콜 차이(표본 수 등)가 섞임 — 표에 각 수치의 측정 조건을 반드시 병기해야 오독을 막음.
- **되돌림 조건**: 향후 π0.5가 단일-step·transformers-4.40 호환 형태로 제공되면 통합 `/act` 어댑터로 흡수하도록 supersede 가능.
