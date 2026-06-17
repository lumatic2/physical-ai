# 0009 - Digital twin layering: keep MuJoCo/Web as public viewer, add backend twin gate

Status: Accepted 2026-06-17

## Context

The project already has a public Robotics Lab at `robotics.askewly.com` backed by MuJoCo WASM, Three.js, ONNX Runtime Web, native rollout artifacts, browser replay, and command-sweep QA.

The user clarified that the target is not a Cosmos-style world model, but a robotics digital twin. In this repo, that means a system that can connect robot assets, physics, controllers, state/action traces, scenario evidence, and eventually telemetry. The current implementation covers the public viewer and lightweight policy sandbox layers, but not real telemetry sync, ROS2/DDS bridging, sensor modeling, or high-fidelity scene authoring.

M19 also shows that the current G1 bottleneck is controlled descent stability, not video generation. The digital twin architecture should therefore preserve MuJoCo native/controller truth while opening a backend stack decision.

## Decision

Keep the existing MuJoCo/Web implementation as the **public twin viewer** and **interactive policy sandbox**.

Open M24 as a **Digital Twin Architecture Gate** instead of replacing the current stack immediately. The next backend candidates are:

- Unitree MuJoCo for G1 state/action trace and SDK/ROS2 compatibility.
- Unitree IsaacLab / Unitree RL Lab for G1 high-fidelity learning and validation.
- Isaac Sim / Isaac Lab for OpenUSD scene, sensor, synthetic data, and robot learning workflows.
- Gazebo / ROS 2 only when real robot telemetry and sensor bridge become the immediate milestone.

Cosmos 3 remains optional as a visual reference or plausibility assistant, not as the twin core or success evidence.

## Consequences

Positive:
- The existing public demo remains valuable and does not get thrown away.
- The next implementation can focus on a measurable backend bridge: state/action trace compatibility with the current web viewer.
- The roadmap can distinguish "viewer", "physics truth", "learning backend", "sensor/scene backend", and "real robot bridge" instead of using "digital twin" as one vague label.

Negative:
- Full telemetry-synced digital twin remains incomplete.
- Isaac/ROS2 paths may require heavier local setup than the current MuJoCo/Web stack.
- The project must keep generated visual/world-model artifacts separate from native simulation evidence.

Follow-up:
- Run `experiments/33-unitree-mujoco-g1-bridge-probe` before any broad rewrite.
- Use `experiments/32-digital-twin-architecture-gate/README.md` as the M24 decision artifact.
