# 54-g1-actuator-authority-probe — G1 actuator authority vs visible squat

> `experiments/54-g1-actuator-authority-probe/README.md` — 실험은 가설/방법/결과/통찰 4섹션.

## 1. 가설 (Hypothesis)

웹 검색상 Unitree G1은 기구학적으로 squat-like 자세를 담을 가능성이 있다. 다리 6DoF와 23DoF 기본형이 공개 문서에 적혀 있고, lower-body joint limits는 hip pitch `-2.5307~2.8798rad`, knee `-0.087267~2.8798rad`, ankle pitch `-0.87267~0.5236rad`로 표시된다. 같은 공개 문서의 joint motor 설명은 최대 120Nm급 모터와 dual encoder를 언급한다. 따라서 현재 M19 실패가 단순 관절 범위 부족이 아니라 MuJoCo position actuator의 추적 authority 또는 stance/contact controller 병목이라면, lower-body gain/bias를 올린 시뮬레이션 probe에서 visible-depth가 안정적으로 늘어야 한다.

근거:
- Unitree G1 developer/spec page, knee max torque 90Nm/120Nm 표기. URL: https://support.unitree.com/home/en/G1_developer, access date: 2026-06-18.
- Unitree G1 overview, lower-body DoF, 23DoF, joint limits, joint motor 120Nm 설명. URL: https://www.docs.quadruped.de/projects/g1/html/g1_overview.html, access date: 2026-06-18.
- MuJoCo actuator docs: gain/bias parameters can represent position/velocity servos, and actuator force clamping/forcerange are separate controls. URL: https://mujoco.readthedocs.io/en/stable/computation/index.html, access date: 2026-06-18; URL: https://mujoco.readthedocs.io/en/stable/XMLreference.html, access date: 2026-06-18.

## 2. 방법 (Method)

### 셋업
- 모델: local G1 MuJoCo model through exp52 `ContactAwareSquat`.
- 데이터: exp52 contact-aware height controller, exp46 stabilizer policy params, exp36 foot-fixed IK target, exp37 support metric.
- 하네스 구성: learning experiment. Raw evidence는 `verify/actuator-authority/`에 저장.

### 시나리오
- Baseline: exp53와 같은 8cm target envelope를 gain 1.0으로 재실행.
- Authority probe: MuJoCo position actuator의 lower-body `gainprm[0]`과 `biasprm[1]`을 같이 1.5배/2.0배로 스케일.
- Ankle probe: ankle pitch/roll은 추가 3.0배를 곱해 stance authority가 병목인지 확인.
- physical-robot claim은 하지 않는다. 이 실험은 “시뮬레이션 actuator authority 진단”이다.

### 측정 metric
- visible pelvis drop, knee/hip pitch delta, fall time, final height/return, both-feet contact ratio, foot slip, joint-limit violation.
- M19 native visible gate: pelvis drop >=8cm, knee delta >=0.60rad, hip pitch delta >=0.35rad, no fall, return/contact/slip gate.

## 3. 결과 (Results)

### 데이터

| Run | Verdict | Lower x | Ankle extra x | Drop | Contact | Slip | Fell | 비고 |
|-----|---------|---:|---:|---:|---:|---:|---|------|
| baseline-gain1p0 | STANCE_ENVELOPE_BROKEN | 1.00 | 1.00 | 1.5054m | 0.81 | 0.909m | 4.54s | exp53 8cm stance cliff 재현 |
| lower-gain1p5 | STABLE_BUT_SHALLOW | 1.50 | 1.00 | 0.0191m | 1.00 | 0.019m | never | best no-fall, but shallow |
| lower-gain2p0 | STABLE_BUT_SHALLOW | 2.00 | 1.00 | 0.0024m | 0.99 | 0.089m | never | 더 stiff해지며 거의 안 내려감 |
| lower-gain1p5-ankle3p0 | STANCE_ENVELOPE_BROKEN | 1.50 | 3.00 | 1.5154m | 0.71 | 0.427m | 1.72s | ankle 증폭은 조기 collapse |
| lower-gain2p0-ankle3p0 | STANCE_ENVELOPE_BROKEN | 2.00 | 3.00 | 1.5185m | 0.67 | 0.573m | 1.30s | best depth is fall |

### 박제 위치
- `verify/actuator-authority/result.json`
- `verify/actuator-authority/authority-probe-summary.md`
- `verify/actuator-authority/*/native-eval.json`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- G1 공개 스펙과 local joint limits만 보면 squat-like pose 자체는 plausible이다. 하지만 현재 M19 실패는 “range가 없어서 못함”이 아니다.
- 단순 lower-body actuator gain 증폭은 stable visible squat를 만들지 못했다. 1.5배는 contact/slip/return은 좋지만 1.9cm shallow이고, ankle까지 세게 올리면 visible-depth 대신 조기 낙상으로 간다.
- 다음 병목은 actuator authority 단일 축보다 CoM/ZMP 또는 whole-body force distribution이다. contact-aware controller가 하강을 억제하거나, 하강이 커지는 순간 support geometry가 깨진다.

### 가설은 통과했나?
- [ ] PASS
- [x] FAIL — authority를 올려도 native visible gate가 안정적으로 열리지 않았다.

### 정의에 반영
- M19는 계속 open. visible squat gate는 유지한다.

### 다음 실험 후보
- explicit CoM/ZMP target 또는 centroidal/whole-body force distribution probe. 단순 gain/torque 배율 반복은 우선순위를 낮춘다.
