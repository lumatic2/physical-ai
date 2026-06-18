# Experiment 124 - G1 Ball Kick Contact Probe

## Question

Can the G1 ball scene produce real foot-ball contact, ball movement toward the target direction, and a no-fall metric in one measurable probe?

## Method

This experiment uses the existing `g1_ball_tap` skill contract and `scene_g1_ball.xml`. It adds explicit `left_foot_ball` and `right_foot_ball` contact pairs because the G1 feetonly model uses explicit contact pairs instead of broad collision masks. The probe replays a scripted right-foot front-kick pose while leaving the ball dynamic in MuJoCo.

This is not a learned policy. It is a contact/reward observability gate for the later learned external-object skill.

## Result

Run:

```powershell
python experiments\124-g1-ball-kick-contact-probe\evaluate_kick_contact.py
```

Current gate: PASS

- Contact frames: `50`
- First contact: `0.396s`
- Ball distance: `1.305m`
- Direction error: `0.148 rad`
- Fell: `false`
- Ball distance threshold: `>= 0.6m`
- Direction error threshold: `< 0.20 rad`
- Fall threshold: base height must stay `>= 0.58m`

## Interpretation

The previous M21 smoke proved only that ball metrics worked when velocity was injected. This probe closes the missing contact path: the same scene can now report foot-ball contacts, object displacement, direction error, and fall/no-fall.

The remaining gap is control quality. A learned policy still needs to solve balance, timing, and energy under the same metrics instead of using the scripted leg replay.

## Evidence

- `evaluate_kick_contact.py`
- `verify/g1-ball-kick-contact-probe.json`
- `verify/g1-ball-kick-contact-probe.md`
