# ADR 0013 — 관찰 가능한 시각-언어-행동 로봇팔 실험실

- Status: Accepted
- Date: 2026-07-20

## Context

기존 공개 Robotics Lab은 MuJoCo physics, learned locomotion policy, replay, telemetry-shaped stream과 evidence gate를 갖췄지만 방문자에게는 로봇 갤러리와 디지털 트윈 환경으로 먼저 보인다. 사용자는 특정 제조사나 Unitree 기종보다, 카메라와 센서가 장면을 관측하고 언어 지시가 행동으로 바뀌며 그 전 과정을 사람이 이해할 수 있는 피지컬 AI 실험실을 대표 결과물로 원한다.

레포의 LIBERO/OpenVLA 평가기는 이미 `camera + instruction -> action -> env.step()` 루프를 실행하지만 main/wrist camera, robot state, VLM/VLA/controller 경계와 결과가 공개 화면의 같은 시간축에 보존되지 않는다.

## Decision

새 flagship Horizon을 **보고 판단하고 움직이는 로봇팔 실험실**로 연다.

- 첫 environment는 기존 LIBERO/robosuite/MuJoCo 경로를 재사용한다.
- 첫 VLA 후보는 multiple camera/state/instruction 계약을 가진 LeRobot-compatible SmolVLA checkpoint를 probe하고, 호환 실패 시 기존 OpenVLA path를 fallback으로 쓴다.
- structured VLM observation 또는 skill selection은 별도 source lane으로 기록한다. VLA의 숨은 사고 과정으로 표현하지 않는다.
- 로컬 GPU run이 canonical PASS/FAIL episode를 만들고, 공개 Vercel app은 versioned trace를 결정론적으로 재생한다.
- 공개 UI는 `recorded evidence`와 `live/local inference`, `simulation`과 `real telemetry`를 구분한다.
- 실물 robot state가 동기화되기 전에는 이 제품을 real-robot digital twin으로 주장하지 않는다.

## Consequences

- 기존 Unitree/MuJoCo 작업은 폐기하지 않고 physics/controller evidence lane으로 남는다.
- 새 Horizon은 모델 학습 경쟁보다 observation/action provenance와 이해 가능한 UI를 우선한다.
- 상시 inference backend 없이도 공개 증거를 먼저 닫을 수 있다.
- 카메라 media와 episode trace의 크기·동기화·revision 관리가 새 품질 게이트가 된다.
- 계층형 agent와 end-to-end VLA를 같은 용어로 섞지 않고 화면에서 비교할 수 있다.
