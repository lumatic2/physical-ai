# GEN5 — Public Generalization Lab

GEN1~GEN4의 고정 분모, 두 VLA 실제 결과, 관측 가능한 실패 양상을 기존 공개 LAB3 episode와 연결한다. 이 폴더는 공개 registry generator와 단계별 QA 정본을 보관한다.

## Step 1 — deterministic public index

`gen_public_index.py`는 60 paired cell·120 recorded episode·27 failure record를 공개 allowlist로 변환한다. 로컬 artifact path와 secret은 포함하지 않으며 두 LAB3 episode만 exact policy/task/state와 hash를 가진 public drill-down으로 노출한다.

```bash
python experiments/154-public-generalization-lab/gen_public_index.py
python experiments/154-public-generalization-lab/test_gen_public_index.py
```

Claim boundary: recorded LIBERO simulator evidence only; not a general winner, root cause, live inference, independent-human review, or real-robot claim.
