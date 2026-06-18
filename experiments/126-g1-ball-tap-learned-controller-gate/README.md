# Experiment 126 - G1 Ball Tap Learned Controller Gate

## Question

Can the M21 scripted ball-tap feasibility work be upgraded into a train/eval gate where a controller candidate is selected by an optimizer and then judged by native MuJoCo metrics?

## Method

This experiment trains a low-dimensional open-loop right-leg controller. It is not a neural RL policy. The controller has seven parameters:

- right hip pitch / roll / yaw
- right knee
- right ankle pitch
- swing start time
- swing duration

The training loop uses seeded random search over those parameters. Each candidate is evaluated in `scene_g1_ball.xml` against the M21 `g1_ball_tap` contract:

- foot-ball contact
- ball distance
- ball direction error
- base-height fall threshold
- energy proxy

The best controller is then re-evaluated with trajectory capture.

## Result

Run:

```powershell
python experiments\126-g1-ball-tap-learned-controller-gate\train_ball_tap_controller.py
```

Current gate: PASS

- Contact frames: `110`
- Ball distance: `5.583m`
- Direction error: `0.034rad`
- Min base height: `0.755m`
- Fell: `false`
- Optimizer: seeded random search over 7 controller parameters

## Interpretation

This closes M25 as a trainable-controller gate: the external-object task is no longer only a scripted contact probe, because the selected controller comes from a repeatable train/eval harness and passes the M25 native metrics.

This still does not claim a full neural RL policy or learned dynamic balance. The base pose remains scripted, and a future milestone should decide whether to replace this controller with PPO/MJX training or a WBC-in-loop policy.

## Evidence

- `train_ball_tap_controller.py`
- `verify/g1-ball-tap-learned-controller-gate.json`
- `verify/g1-ball-tap-learned-controller-gate.md`
- `verify/g1-ball-tap-learned-controller-trajectory.json`
