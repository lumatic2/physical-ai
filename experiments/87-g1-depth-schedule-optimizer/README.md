# Experiment 87: G1 Depth Schedule Optimizer

## Hypothesis

G1 squat is physically plausible, but M19 is not just a geometry question. The missing question is whether a controller can produce a visible squat while keeping foot contact, slip, and terminal recovery inside the gate.

Web search before running this experiment supports that split. External sources, accessed 2026-06-18:

- https://www.unitree.com/g1/ — Unitree lists G1 as a 35kg humanoid with 6 DoF per leg, knee joint range 0-165 degrees, hip pitch +/-154 degrees, and maximum knee torque up to 90Nm or 120Nm depending on configuration.
- https://agile.human2humanoid.com/ — ASAP reports Unitree G1 whole-body skills including squat and squat plus lean, but the method uses motion tracking, residual alignment, and real-world fine-tuning rather than raw pose tracking.
- https://hugwbc.github.io/ — HUGWBC frames fine-grained humanoid locomotion as a whole-body control problem, matching the evidence that stance/contact control is the limiting factor here.

The testable hypothesis was that exp86's recoverable 5cm three-phase controller can be used as a safety teacher, and a small depth schedule optimizer can expand it toward the 8cm visible gate without immediately switching to a new learned policy.

## Method

The runner copies exp86's three-phase controller:

- `descend`: visible squat target with bounded knee/hip pose bias.
- `recapture`: support/ZMP/slip-heavy crouch hold.
- `stand`: default stand recovery with stronger terminal stand, contact, and slip costs.

The new part is a 10-candidate schedule search around the exp86 safe branch. Each candidate gets a full 6s native rollout, the exp29 visible gate metrics, and an optimizer score that penalizes fall, depth/knee/hip shortfall, slip excess, contact loss, return shortfall, and negative support/ZMP margins.

Raw command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\87-g1-depth-schedule-optimizer\run_depth_schedule_optimizer.py --seconds 6.0
```

Output files:

- `verify/depth-schedule-optimizer/result.json`
- `verify/depth-schedule-optimizer/depth-schedule-optimizer-summary.md`
- `verify/depth-schedule-optimizer/*/native-eval.json`

## Results

Verdict: `FAIL_VISIBLE_8CM_GATE`.

Best optimizer run:

- Attempt: `sched-8cm-return-heavy`
- Visible drop: `0.0947m` PASS
- Knee delta: `0.430rad` FAIL
- Hip pitch delta: `0.370rad` PASS
- Both-foot contact ratio: `0.87` FAIL
- Foot slip: `0.106m` FAIL
- Final height: `0.6603m` FAIL
- Fell at: none
- Verdict: `POSE_GATE_PENDING`

Best no-fall depth run:

- Attempt: `sched-8cm-low-residual`
- Visible drop: `0.2919m` PASS
- Knee delta: `0.433rad` FAIL
- Hip pitch delta: `0.277rad` FAIL
- Both-foot contact ratio: `0.84` FAIL
- Foot slip: `0.111m` FAIL
- Fell at: none

The safe teacher branch remained recoverable but shallow:

- Attempt: `teacher-safe-5cm`
- Visible drop: `0.0507m`
- Contact: `0.98`
- Slip: `0.052m`
- Final height: `0.7387m`
- Fell at: none

## Insights

The robot is not the blocker in the narrow sense: the web evidence and local rollouts both show that G1 can enter visible squat-like configurations. The blocker is controlled recoverability under the M19 gate. Exp87 improved over exp86 by finding a no-fall 9.47cm schedule with hip gate pass, but that schedule gives up knee flexion, contact, slip, and terminal stand height.

The next experiment should not just widen this hand-written grid. The useful signal is now clear enough for targeted learning: use exp87's no-fall visible schedules as positive geometry teachers and exp86's 5cm branch as the safety teacher, then train or optimize knee/contact/return jointly instead of tuning schedule constants by hand.
