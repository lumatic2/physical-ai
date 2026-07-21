# SO-101 sim-to-real 증거 루프 조사

- 조사일: 2026-07-21
- 소비처: `sim-real-so101-evidence-loop`
- 질문: 실물 로봇이 없는 현재 상태에서 어떤 외부 게이트와 증거 계약으로 SO-101 Horizon을 계획할 수 있는가?

## 결론

SO-101 leader+follower, front+wrist camera와 물리 emergency stop을 실제 획득한 뒤 LeRobot 공식 calibration→teleoperation→dataset→ACT evaluation 흐름을 따른다. 구매는 코드 실행 승인과 별개이며 사용자의 예산·배송·공간 확인 전에는 REAL1을 진행하지 않는다. 시뮬레이션과 실물은 성공률을 직접 동치 비교하지 않고 동일 episode schema와 claim boundary만 비교한다.

## 근거

- LeRobot 공식 실물 로봇 문서는 SO-101 follower/leader id별 calibration, teleoperation, camera가 포함된 dataset recording과 policy evaluation 흐름을 제공한다. 출처: https://github.com/huggingface/lerobot/blob/main/docs/source/il_robots.mdx (접근일: 2026-07-21)
- LeRobot agent guide는 SO-101 시작 전 하드웨어·teleop·camera·training machine 확인을 요구하고, 50 episode dataset과 eval dataset 저장·success rate 비교 경로를 제시한다. 출처: https://github.com/huggingface/lerobot/blob/main/AGENT_GUIDE.md (접근일: 2026-07-21)
- LeRobot HIL data collection은 SO-101 leader arm takeover와 DAgger rollout을 지원한다. 첫 real baseline 뒤 안전한 intervention data로 확장할 수 있지만 첫 Horizon의 필수 범위에서는 제외한다. 출처: https://github.com/huggingface/lerobot/blob/main/docs/source/hil_data_collection.mdx (접근일: 2026-07-21)
- LeRobotDataset은 Parquet와 video를 사용해 실물 episode를 기존 LAB evidence 계약과 연결할 수 있다. 출처: https://github.com/huggingface/lerobot (접근일: 2026-07-21)

## 채택 결정

1. 하드웨어 기준은 SO-101 leader+follower, front+wrist camera, 독립 전원 차단과 제한된 작업 공간이다.
2. 과제는 black cube를 고정 target zone으로 옮기는 단일 조작이며 50 teleop training episode와 30 unseen-condition evaluation episode를 기본 분모로 한다.
3. 첫 real policy는 LeRobot ACT다. SmolVLA/HIL은 후속 후보로 남긴다.
4. sim analogue와 real task는 schema를 공유하지만 physics/performance 동일성을 주장하지 않는다.
5. 원본 영상·state·action·calibration revision·intervention/safety event를 canonical evidence로 보존한다.

## 조사 종료 판단

LeRobot의 calibration, teleop, recording, ACT evaluation, HIL 문서를 대조한 뒤 추가 자료는 조립 부품과 OS별 port 세부만 더했다. acquisition/safety, calibration/teleop, dataset, policy eval, public comparison의 다섯 경계로 포화되어 종료한다.
