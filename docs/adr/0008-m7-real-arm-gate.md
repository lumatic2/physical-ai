# 0008 — M7 실물 도달 게이트: SO-101 2-arm teleop + ACT로 좁히고, 구매 전 준비만 닫는다

- Status: Accepted (2026-06-15)
- 근거 reference: TheRobotStudio/SO-ARM100 (https://github.com/TheRobotStudio/SO-ARM100), Hugging Face LeRobot SO-101 docs (https://huggingface.co/docs/lerobot/so101), Hugging Face ACT-on-SO-101 blog (https://huggingface.co/blog/sherryxychen/train-act-on-so-101), NVIDIA GR00T N1.5 SO-101 blog (https://huggingface.co/blog/nvidia/gr00t-n1-5-so101-tuning)
- 관련: [[0002-act-deferred-to-m6]], [[0004-digital-twin-stack]], M7 실물 도달

## Context

M1-M14로 이 레포는 문헌 지형, VLA 로컬 평가, action-representation 비교, 브라우저 MuJoCo 정책 플랫폼까지 닫았다.
남은 포트폴리오 공백은 **실물 조작**이다. 기존 로드맵은 "SO-100류 저가팔 + ACT"였지만, 2026-06-15 재점검 결과:

- TheRobotStudio는 SO-101을 SO-100의 다음 세대 버전으로 설명한다. 개선점은 wiring, 쉬운 조립(no gear removal), leader arm updated motors다. SO-100 문서는 deprecated로 내려갔다. 접근 2026-06-15.
- SO-101 공식 BOM은 follower+leader 2-arm teleoperation setup을 표준 경로로 둔다. GitHub README 기준 parts total은 US 기준 약 $229.88, follower only는 약 $121.94다. 단 가격·지역·배송은 변동된다. 접근 2026-06-15.
- LeRobot SO-101 문서는 follower와 leader motor gear ratio 차이를 명시한다. 즉 leader/follower를 같은 부품으로 막 사면 teleop 품질과 조립 난도가 흔들린다. 접근 2026-06-15.
- SO-101 위에서 ACT를 학습한 공개 후기와 NVIDIA GR00T N1.5 post-training 예제가 이미 있다. M7의 "실물 + imitation learning" 방향은 더 이상 추상 아이디어가 아니라 실행 경로가 있는 선택지다. 접근 2026-06-15.

## Decision

M7의 하드웨어 경로를 **SO-101 2-arm teleoperation setup + LeRobot + ACT-first**로 좁힌다.

1. **SO-100 신규 구매는 피한다.** 이미 deprecated 취급이고, 이 레포의 SO-100 디지털 트윈은 포트폴리오/시뮬 자산으로 유지한다.
2. **follower-only 구매는 M7 본선이 아니다.** follower-only는 VR/keyboard/hand-coded teleop으로 움직일 수 있지만, ACT용 demonstration data를 빠르게 모으려면 leader arm이 필요하다.
3. **구매 전 게이트를 먼저 닫는다.** 예산, 작업 공간, 카메라 2대, clamp/전원/USB 안정성, LeRobot calibration 시간을 확보하지 못하면 구매하지 않는다.
4. **첫 실물 task는 stacking이 아니라 tabletop pick/place로 낮춘다.** M6에서 확인한 5-DOF top-down lift 한계 때문에, 첫 성공 기준은 "큐브를 지정 구역으로 옮긴다" 수준이어야 한다.
5. **ACT를 1차 학습 정책으로 둔다.** OpenVLA/π0는 이미 sim benchmark에서 실측했으므로, M7의 새 정보량은 ACT-style imitation learning과 reality gap 회고에 있다.

## Consequences

- **(+)** M7이 "무엇을 살까"에서 멈추지 않고, 구매하면 바로 따라갈 수 있는 실행 경로로 좁혀진다.
- **(+)** ADR 0002의 미완 과제(ACT는 실물 모방학습 자리)가 자연스럽게 회수된다.
- **(+)** SO-101 2-arm은 demonstration collection이 단순하다. leader arm 움직임이 follower action 데이터가 되므로, 포트폴리오 결과가 "직접 데이터 수집"으로 보인다.
- **(-)** 실제 M7 완료는 하드웨어 구매·배송·조립·캘리브레이션이라는 외부 상태에 막힌다. 코드만으로 완료할 수 없다.
- **(-)** 2-arm kit는 follower-only보다 비용·공간·배선 리스크가 크다.
- **되돌림 조건**: (a) SO-101 공급/가격이 비정상적으로 나빠지면 follower-only 또는 중고/조립품을 재검토한다. (b) ACT보다 GR00T/LeRobot pretrained 정책이 훨씬 빠른 성공 경로가 되면 ACT-first를 supersede한다.
