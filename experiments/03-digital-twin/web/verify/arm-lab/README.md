# LAB3 공개 reviewer gate

## 5분 검토 체크리스트

1. 첫 화면 상단에서 `RECORDED EVIDENCE`, `LIBERO SIMULATION`과 성공/실패 결과를 확인한다.
2. 재생·일시정지·좌우 한 프레임·scrubber를 조작해 주/손목 camera와 graph cursor가 함께 이동하는지 본다.
3. PASS/FAIL을 바꾸고 두 결과가 같은 정보 밀도와 레이아웃을 유지하는지 본다.
4. `Direct VLA`와 `VLM → bounded skill`을 바꿔 실제 action 주체와 `scripted controller` assistance가 구분되는지 본다.
5. event 하나를 선택하고 `증거 원문 열기`에서 source, parents, revision, assistance, raw artifact 링크를 확인한다.
6. 라이트/다크를 전환하고 좁은 창에서 가로 잘림이나 한글 단어 중간 잘림이 없는지 본다.

## 자동 검증 계약

- Local: `local-player-report.json`과 `local-*.png`.
- Live: 배포 후 `live-player-report.json`과 `live-*.png`.
- PASS 조건: asset 404·console error 0, camera sync delta ≤ 0.08s, graph cursor 동일 frame, mobile horizontal overflow 0.
- Negative: 0.75s camera desync, hidden reasoning, unknown source, live/real claim relabel, camera provenance relabel은 FAIL해야 한다.

## 디자인 출처

- Askewly responsive content grid recipe: https://ui.askewly.com/llms/recipes/layout/responsive-content-grid.md (accessed 2026-07-21)
- Askewly code asset: https://ui.askewly.com/r/responsive-content-grid.json (accessed 2026-07-21)
