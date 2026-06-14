# 0007 — 번들 정책 씬 byte-parity: env 런타임 모델 변경을 정적 번들 xml에 박는다 (M11)

- Status: Accepted (2026-06-15)
- 근거 reference: mujoco_playground `spot/base.py`(런타임 `dof_damping`/`actuator_gainprm` 오버라이드), 자체 M11 byte-parity 디버깅(0.15 발산→2.91e-7)
- 관련: [[0005-learned-policy-sandbox]] sim2sim parity 토대 연장. [[0006-extensible-twin-platform]] 위에서 dogfood. M11 exp 06.

## Context

학습 정책을 브라우저에서 closed-loop로 돌리려면 **번들 씬(웹)이 학습 씬과 byte-parity**여야 한다 — 같은 obs를
넣어야 같은 행동이 나온다([[0005]]가 "최대 리스크"로 박제). Go1/G1은 Menagerie 자산을 거의 그대로 써서 쉽게 맞았다.

Spot(M11)에서 번들 씬 rollout obs가 학습 golden과 **0.15 발산**했다. 모델 필드를 하나씩 diff한 결과:
질량·관성·geom·솔버·timestep·접촉 파라미터는 전부 동일했고, **딱 두 개가 달랐다** — `dof_damping`(번들 2, 학습 1),
`actuator_gainprm`(번들 400, 학습 300). 원인: **playground env가 xml을 로드한 뒤 `base.py`에서 PD 게인을
코드로 덮어쓴다**(`dof_damping[6:]=Kd=1`, `actuator_gainprm[:,0]=Kp=300`, `biasprm[:,1]=-Kp`). 즉 학습에 쓰인
"진짜 모델"은 디스크의 xml이 아니라 **xml + 런타임 패치**다. 정적 번들(xml만)은 이 패치를 못 따라가 미세 발산하고,
그 차이가 closed-loop에서 매 스텝 누적된다.

이건 시각·reward로는 안 잡힌다(둘 다 "그럴듯하게 걷는다"). 모델 필드 diff로만 발견된다.

## Decision

**env가 런타임에 가하는 모델 변경을 찾아 번들 xml에 정적으로 박는다(bake).** 번들 씬을 "학습이 실제로 본 모델"과
일치시키되, 정적 자산만으로.

- Spot: 번들 `spot_mjx_feetonly.xml`의 default 클래스에 `damping="1"`·`kp="300"`(원본 2·400) 직접 기입. 주석으로
  "env base.py의 Kd/Kp 오버라이드를 박은 것"임을 명시.
- 검증 게이트: `rollout_spot.py`가 **번들 씬 rollout obs == 학습 golden_obs**를 assert(< 1e-3). 이 게이트가
  "byte-parity 달성"의 정의 — 통과 후에만 라이브. (결과 2.91e-7.)
- **왜 런타임 패치(JS에서 모델 수정) 아님**: 웹 로더(mujoco-js)에서 모델 필드를 런타임에 바꾸는 것은 깨지기 쉽고
  desktop/web 두 경로를 다 패치해야 함. 정적 bake는 한 곳(xml)에서 desktop·web·QA 전부 일치.
- **왜 "학습 씬 그대로 번들" 아님**: 학습 씬(`scene_mjx_feetonly_flat_terrain.xml`)은 contact 센서(`<contact>`,
  wasm 0.0.7 미지원)와 런타임 패치 의존을 포함 → 그대로는 웹에서 안 뜨거나 발산. 정책 obs에 필요한 센서만 남기고
  PD 게인을 bake한 *파생* 씬이 정답.

## Consequences

- **(+)** Spot byte-parity 2.91e-7 → 웹 closed-loop가 native와 byte-identical(0.93 vs 0.92 m/s, 라이브 QA에서
  로컬과 x 동일). 학습→native→웹→프로덕션 한 줄로 parity.
- **(+)** 재사용 규약 확보: **새 정책 번들 시 "env가 로드 후 모델을 바꾸는가"를 먼저 확인**(PD 게인·timestep·질량
  스케일 등). [[0006]]의 `ADDING_EMBODIMENTS.md`에 반영할 체크포인트.
- **(+)** 진단 방법론 박제: 시각/reward가 아니라 **컴파일된 모델 필드 diff**가 byte-parity 발산의 1차 도구.
- **(−)** bake는 수동(env 소스를 읽어 어떤 필드를 덮어쓰는지 사람이 찾음). env가 더 복잡한 런타임 변경(도메인
  랜덤화 평균값, 관측 정규화 등)을 하면 bake가 누락될 수 있다 — 그래서 rollout 게이트(obs==golden)가 안전망.
- **되돌림 조건**: 런타임 변경이 정적 bake로 표현 불가한 정책(예: env가 매 step 모델을 바꾸는 경우)이 나오면,
  그 정책은 웹 번들 대신 native-only 데모로 강등하거나 web 로더에 모델-패치 훅 도입을 재검토.
