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
