# GEN3 — Paired VLA Comparison

OpenVLA와 π₀.₅-LIBERO를 GEN1의 동일 task/state denominator와 canonical result contract로 비교한다.

## Step 1: π₀.₅ compatibility probe

`probe_pi05.py`는 GEN2의 실제 `libero_spatial/task-00/state-00` canonical episode 첫 관측을 π₀.₅ 입력으로 재사용한다. main/wrist frame은 공식 OpenPI LIBERO client와 같이 180° 회전 후 224×224로 padding-resize하고, 8D state와 고정 instruction을 함께 전달한다.

```bash
cd /home/yusun/openpi-gen3
OPENPI_DATA_HOME=/home/yusun/.cache/openpi-gen3 uv run python \
  /mnt/c/Users/yusun/projects/physical-ai/experiments/152-paired-vla-comparison/probe_pi05.py \
  --sample-dir /home/yusun/physical-ai-runs/gen2-openvla/episodes/libero_spatial-task-00-state-00/attempt-6c1ea86fa57247c4abcda83350eff013 \
  --checkpoint-dir /home/yusun/.cache/openpi-gen3/openpi-assets/checkpoints/pi05_libero
```

검증 경계: 이 probe는 정확한 checkpoint가 한 실제 관측에서 finite 10×7 action chunk를 낸다는 호환성 증거다. rollout 성공률이나 정책 우열 증거가 아니다.

## Step 2: shared adapter parity

`shared-adapter-contract.json`은 두 정책의 공통 캡처·결과 외피와 정책별 model input, 전처리, action chunk, gripper 변환을 함께 고정한다. 공정성은 동일 task/state/environment/result denominator이며 입력을 동일하다고 가장하지 않는다.

```bash
python experiments/152-paired-vla-comparison/verify_adapter_parity.py
```

## Step 3: π₀.₅ 60-cell execution

`execute_pi05.py`는 GEN1의 정확한 π₀.₅ 60개 run key를 순서대로 실행한다. 하나의 OpenPI policy server를 재사용하고, 각 attempt를 append-only ledger에 남긴 뒤 raw LeRobot dataset·provenance sidecar·causal event를 검증한 cell만 sealed result로 승격한다.

```bash
cd /mnt/c/Users/yusun/projects/physical-ai
MUJOCO_GL=egl /home/yusun/.venvs/vla-eval/bin/python \
  experiments/152-paired-vla-comparison/execute_pi05.py \
  --artifact-root /home/yusun/physical-ai-runs/gen3-pi05 \
  --ledger /home/yusun/physical-ai-runs/gen3-pi05/run-ledger.jsonl \
  --client-python /home/yusun/.venvs/vla-eval/bin/python \
  --server-python /home/yusun/openpi-gen3/.venv/bin/python \
  --server-root /home/yusun/openpi-gen3 \
  --libero-root /home/yusun/LIBERO \
  --openpi-data-home /home/yusun/.cache/openpi-gen3
```

완료 뒤 canonical index는 원 ledger와 episode tree를 다시 읽어 생성한다.

```bash
/home/yusun/.venvs/vla-eval/bin/python \
  experiments/152-paired-vla-comparison/verify_pi05_execution.py \
  --artifact-root /home/yusun/physical-ai-runs/gen3-pi05 \
  --ledger /home/yusun/physical-ai-runs/gen3-pi05/run-ledger.jsonl \
  --assert-clean-processes
```

검증 경계: infrastructure error attempt는 보존하되 정책 success/timeout 분모에 섞지 않는다. 이 Step은 π₀.₅ 60개 rollout의 실제 실행 증거이며 paired 통계와 정책 우열 해석은 Step 4 이후에만 연다.

실측 결과: 60/60 terminal, 58 success·2 timeout, 7,608 frames, 1,545 policy requests, suite별 20개다. 첫 cell의 환경 설정 실패 2건은 별도 infrastructure attempt로 ledger에 남고 정책 분모에는 포함되지 않는다.
