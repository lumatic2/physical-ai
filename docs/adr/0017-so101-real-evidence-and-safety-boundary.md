# ADR 0017 — SO-101 실물 증거와 안전 경계

- 상태: proposed
- 날짜: 2026-07-21

## 결정

- actual hardware acquisition은 Horizon 실행 승인과 분리된 사용자 외부 게이트다.
- SO-101 leader/follower, front/wrist camera, physical power cut와 제한 workspace가 준비돼야 REAL1을 시작한다.
- LeRobot calibration id와 raw camera/state/action/safety event를 canonical evidence에 포함한다.
- 첫 정책은 ACT, dataset은 50 teleop episode, unseen-condition evaluation은 30 episode로 고정한다.
- sim과 real은 schema와 evidence coverage만 비교하며 physics 또는 success rate 동치를 주장하지 않는다.

## 근거

- https://github.com/huggingface/lerobot/blob/main/docs/source/il_robots.mdx (접근일: 2026-07-21)
- https://github.com/huggingface/lerobot/blob/main/AGENT_GUIDE.md (접근일: 2026-07-21)
- `research/2026-07-21-sim-real-so101-evidence-loop.md`
