# Experiment 76: G1 Knee-Flexion Microphase

## Hypothesis

Unitree G1로 squat-to-height 류 동작은 공개 연구에서 가능해 보인다. 다만 우리 M19 gate는 단순히 pelvis가 낮아지는 것이 아니라 `pelvis drop >= 8cm`, `knee flexion delta >= 0.60rad`, `hip pitch delta >= 0.35rad`, no-fall, stance/contact, return-to-stand를 동시에 요구한다. 그래서 selector score만 바꾸는 exp75 다음 가설은, support/ZMP/slip health가 충분할 때만 짧은 knee-flexion micro-phase를 IK target family에 넣으면 0.513rad knee plateau를 넘을 수 있다는 것이다.

## Method

`experiments/71-g1-event-triggered-recapture/run_event_triggered_recapture.py`의 native evaluator와 gates를 재사용했다. `EXP62.build_target`만 monkeypatch해 `desired_fraction` window 안에서 left/right knee target을 positive bias, hip pitch target을 small negative bias로 보정했다.

Raw evidence:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; C:\tmp\e34\Scripts\python.exe .\experiments\76-g1-knee-flexion-microphase\run_knee_flexion_microphase.py
```

Output files:

- `verify/knee-flexion-microphase/result.json`
- `verify/knee-flexion-microphase/knee-flexion-microphase-summary.md`
- `verify/knee-flexion-microphase/*/native-eval.json`

External sources, accessed 2026-06-18:

- https://pmc.ncbi.nlm.nih.gov/articles/PMC11769464/ — humanoid squatting is framed as trajectory-level whole-body coordination.
- https://www.lirmm.fr/krut/pdf/2014_galdeano_ssd-0568454426/2014_galdeano_ssd.pdf — WBC posture transitions combine CoM/ZMP, feet pose, and joint objectives.
- https://arxiv.org/html/2502.17219v1 — ZMP inside support polygon is used as a humanoid balance condition.
- https://www.roboticsproceedings.org/rss21/p070.pdf — recent Unitree G1 work motivates explicit knee-flexion shaping for squat-to-height behavior.

## Results

Verdict: `PASS_RECOVERABLE_7CM_GATE`, not `PASS_VISIBLE_8CM_GATE`.

Best recoverable/no-fall candidate:

- Attempt: `focus-k0p11-h0p03-p0p55-0p75-0p95-mh0p80`
- Visible drop: `0.0770m`
- Knee delta: `0.516rad`
- Hip pitch delta: `0.330rad`
- Foot contact ratio: `0.98`
- Foot slip: below gate (`slip_excess_m = 0.0`)
- Final height: `0.7497m`
- Visible gate gap: `0.0030m` drop, `0.0836rad` knee, `0.0200rad` hip

Best depth branch was not usable:

- Attempt: `micro-k0p06-h0p02-p0p35-0p55-0p75-mh0p45`
- Visible drop: `1.5353m`
- Knee delta: `0.588rad`
- Fell at: `5.82s`
- Transition verdict: `FAIL_FALL`

## Insights

The web search answer is: **yes, a G1-class humanoid can plausibly perform squat-to-height behavior**, but our current controller family still cannot pass the visible squat gate. The local experiment moved the recoverable boundary from about `7.61cm` to `7.70cm` and improved hip gap, but the stable knee flexion plateau only shifted from about `0.513rad` to `0.516rad`.

The important split is now clear: pushing knee flexion harder does create larger knee motion in the fall branch, but it couples into late support/ZMP collapse instead of a recoverable squat. The next useful experiment should stop patching `build_target` alone and introduce a custom descend-only phase evaluator or trajectory optimizer that can keep knee flexion through descent while separately planning CoM/ZMP and return.
