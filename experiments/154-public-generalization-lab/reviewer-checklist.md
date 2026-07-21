# 공개 일반화 실험실 — 5분 reviewer checklist

## 1분 — 비교 분모

- 첫 화면에서 `60쌍`, `120 recorded episode`를 찾는다.
- OpenVLA `35/60`, π0.5-LIBERO `58/60`, 관측 paired 차이 `+23/60`을 확인한다.
- planned/included/excluded/unmatched가 `60/60/0/0`인지 확인한다.

## 2분 — 필터와 실패 양상

- Spatial/Object/Goal을 눌렀을 때 각각 `20쌍`이 되는지 본다.
- 한 task를 선택하면 `5쌍`이 되는지 본다.
- 실패 양상에서 `27 = no_progress 6 + unknown 21`인지 확인한다.
- unknown 정의와 판정하지 않은 세 양상이 숨겨지지 않았는지 본다.

## 1분 — 원 증거 연결

- Spatial → Task 05 → state 00 또는 state 01을 선택한다.
- `이 OpenVLA episode를 듀얼 카메라로 보기`를 연다.
- LAB3 상단 provenance 배너의 source cell·manifest와 PASS/FAIL 선택이 일치하는지 본다.
- 주 카메라와 손목 카메라가 모두 보이는지 확인한다.

## 1분 — 주장 경계

- 이것이 recorded LIBERO simulation이며 live inference나 real robot telemetry가 아님을 확인한다.
- 결과를 general winner나 root-cause diagnosis로 표현하지 않았는지 본다.
- 모바일 폭에서 가로 스크롤 없이 필터와 evidence row를 읽을 수 있는지 본다.
