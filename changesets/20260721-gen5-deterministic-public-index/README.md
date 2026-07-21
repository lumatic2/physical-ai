# Changeset: GEN5 deterministic public index

- Status: completed
- Target: ROADMAP `GEN5` step-1 — `deterministic-public-index`

## Scope

- GEN1~GEN4 canonical reports를 공개 필드 allowlist로 변환한다.
- 60 paired cell·120 policy episode·27 failure를 raw numerator/denominator와 hash로 보존한다.
- LAB3 PASS/FAIL을 OpenVLA spatial task 5, state 0/1에 연결한다.
- local path, token, stale camera hash와 unsupported claim을 차단한다.

## Verification

- [x] 동일 input에서 byte-identical registry다.
- [x] 60 cell·120 episode·27 failure·21 unknown이 보존된다.
- [x] 공개 bundle이 256KB 이하이고 로컬 경로·token이 없다.
- [x] LAB3 두 episode의 outcome·state·dataset/camera hash가 맞는다.
- [x] missing denominator·stale hash·unsafe path/token·unsupported claim이 FAIL한다.

## Result

65,992-byte canonical registry를 생성했다. 60 paired cell, 120 policy episode, success 93·timeout 27, no_progress 6·unknown 21이 보존된다. LAB3 PASS/FAIL은 OpenVLA `libero_spatial/task-05/state-00/01`에 연결되며 dataset tree와 main/wrist camera SHA가 canonical evidence와 일치한다.

동일 input은 SHA-256 `cda4f01adf2481c43c939e4390bf5202ab481bf67d3192bbc338e9b58c229713`의 byte-identical registry를 만든다. 6개 focused test와 compile/diff gate가 통과했다.
