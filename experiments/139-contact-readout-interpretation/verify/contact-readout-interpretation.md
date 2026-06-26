# Contact Readout Interpretation

Generated: 2026-06-26T06:15:54.234Z

## Supported
- Browser MuJoCo runtime exposes ncon/contact/cfrc_ext/sensordata readout fields.
- Keyboard command changes and runtime readout snapshots can be recorded in one same-run timeline.
- The evidence supports a simulator-state readout claim for the browser workbench.

## Not Supported
- It does not prove calibrated contact force accuracy.
- It does not prove causal attribution from command input to every readout delta.
- It is not real robot telemetry.

## Source Evidence
- Timeline: experiments/138-command-contact-timeline/verify/command-contact-timeline.json
- Local pass: true
- Live pass: true
