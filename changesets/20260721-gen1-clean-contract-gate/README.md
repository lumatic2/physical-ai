# Changeset: GEN1 clean contract gate

- Status: completed
- Target: ROADMAP `GEN1` step-5 — `clean-contract-gate`

## Scope

- `verify_contract.py`: task/state/policy/denominator와 canonical evidence를 연결한 통합 gate.
- `fixtures/integrated-contract-mutations.json`: cell 삭제·중복·environment revision drift 주입 명세.
- `test_verify_contract.py`: 로컬 통합 PASS와 세 변이의 거부를 회귀 검사.
- `verify/canonical/gen1-contract-report.json`: 공식 LIBERO/openpi source와 live π0.5 GCS snapshot까지 대조한 정본 증거.

## Contract

- 완전성: 12 task × 5 initial state × 2 policy = 120 unique cell.
- 고정점: manifest/state/registry/denominator content hash와 공식 source revision.
- 공개 안전: repo 산출물의 로컬 사용자 경로와 값이 든 secret 할당을 거부한다.
- 주장 경계: GEN1은 평가 identity와 evidence requirement만 고정하며 policy 성능은 주장하지 않는다.

## Verification

- [x] 120 planned / 120 unique cell과 네 canonical evidence hash PASS.
- [x] 공식 LIBERO 12 BDDL 및 openpi registry source revision 대조 PASS.
- [x] live π0.5 checkpoint 16 object / 12,439,085,481 byte snapshot 대조 PASS.
- [x] cell 삭제·중복·environment revision drift 변이를 모두 거부.
- [x] Windows `core.autocrlf=true` clean checkout에서 동일 통합 gate 재실행 PASS.

## Result

12×5×2의 120개 cell, 네 canonical evidence hash, 공식 LIBERO/openpi source와 live π0.5 checkpoint snapshot이 현재 checkout과 clean checkout에서 모두 PASS했다. 첫 clean probe는 repo 텍스트 hash가 checkout 줄바꿈에 의존해 FAIL했고, repo 내부 텍스트만 Git 정본 LF로 정규화해 재검증했다. 외부 BDDL과 state binary는 raw byte hash를 유지한다.

## Sources

- [LIBERO commit](https://github.com/Lifelong-Robot-Learning/LIBERO/tree/8f1084e3132a39270c3a13ebe37270a43ece2a01) (접근일: 2026-07-21)
- [openpi commit](https://github.com/Physical-Intelligence/openpi/tree/15a9616a00943ada6c20a0f158e3adb39df2ccac) (접근일: 2026-07-21)
- [π0.5 LIBERO checkpoint listing](https://storage.googleapis.com/storage/v1/b/openpi-assets/o?prefix=checkpoints/pi05_libero/) (접근일: 2026-07-21)
