# 최종 보고서 — LAB3 공개 관찰형 로봇팔 실험실

> 완료: 2026-07-21 · 대상: LAB3 · 작성: 완료 경계(§B3) — 이 보고서가 완료 의식의 정본이다.

## 1. 문제 정의 (무엇을 왜 하려 했나)

LAB1과 LAB2에서 실제 OpenVLA·Qwen3-VL/LIBERO 실행 증거를 만들었지만, 외부 사람이 이를 한 화면에서 보고 검토할 제품 표면은 없었다. 사용자가 원한 것은 카메라가 달린 로봇팔이 장면을 보고 언어 지시를 이해하며 행동하고, 판단과 결과의 출처를 사람이 관찰할 수 있는 실험실 화면이었다. LAB3는 canonical 기록을 과장 없이 공개 재생하고 5분 안에 관측→판단→행동→결과를 이해할 수 있게 만드는 것을 목표로 했다.

## 2. Objective 연결 (북극성과의 관계)

Objective의 “카메라와 센서로 세상을 보고, 언어 지시를 이해하고, 로봇 행동을 생성·실행하며, 그 전 과정을 사람이 관찰할 수 있는 피지컬 AI 실험실”을 공개 제품 표면으로 완성했다. 기록된 simulation이라는 경계를 유지하면서도 모델 입력 camera, 관찰 전용 camera, VLM/VLA/controller/environment source와 outcome을 같은 시간축에서 직접 검토할 수 있다.

## 3. 경로 (horizon → milestone → steps)

“보고 판단하고 움직이는 로봇팔 실험실” Horizon의 세 번째 milestone으로 진행했다. 첫 step에서 LAB1/LAB2 정본을 content-hashed 공개 bundle로 변환했고, 두 번째에서 dual-camera·공통 playback·graph cursor를 동기화했다. 세 번째에서 Direct VLA와 VLM→bounded skill 인과 timeline 및 evidence drawer를 연결했다. 네 번째에서 local reviewer gate, UI polish, production 배포와 live gate를 통과했다. 승인된 계획에서 벗어난 backend·로그인·live GPU 추론·실물 telemetry는 추가하지 않았다.

## 4. 구현 결과 (무엇이 만들어졌나)

공개 방문자는 PASS/FAIL episode와 Direct VLA/VLM→bounded skill lane을 전환하고, 주 카메라와 손목 카메라를 같은 scrubber로 재생할 수 있다. 선택 frame과 state/action graph cursor, 현재 causal event가 함께 움직이며 각 event의 source, parent, component revision, assistance, artifact hash를 evidence drawer에서 확인한다. 화면은 `RECORDED EVIDENCE`와 `LIBERO SIMULATION`을 상시 표시하고 free-form chain-of-thought나 real/live telemetry로 오해할 표현을 거부한다. 데스크톱 light/dark와 모바일 반응형 화면, 데이터 로드 실패 복구와 PASS/FAIL 의미 색상도 포함한다.

## 5. 이슈와 해결 (막혔던 것, 어떻게 풀었나)

처음에는 전체 LeRobot Dataset Visualizer를 재사용하는 후보를 검토했지만 현재 앱과 결합 비용이 커서 multi-video, 공통 playback, cursor 패턴만 선택 이식했다. 공개 전 사람 확인이 필요한 디자인 gate에서는 사용자가 화면을 보기 어려운 상황이라 배포를 보류하고 local evidence만 고정했으며, 이후 사용자의 명시적 배포 지시로 gate를 해소했다. 첫 배포 명령은 실행 래퍼의 5초 제한으로 중단돼 충분한 제한으로 재실행했다. 첫 live QA는 React 전환보다 단언이 빠른 경쟁 조건을, 두 번째는 실패 배지가 현재 사건과 timeline 두 곳에 정상 표시돼 strict locator가 2개를 잡는 문제를 드러냈다. 제품 결함이 아님을 공개 bundle과 DOM으로 확인한 뒤 QA를 timeline 결과 카드로 한정하고 visibility를 기다리게 수정해 재발을 막았다.

## 6. 결과물과 증거 (검증 포함)

- Changesets: `changesets/20260721-lab3-public-evidence-bundle/`, `changesets/20260721-lab3-synchronized-dual-camera-player/`, `changesets/20260721-lab3-causal-timeline-evidence-drawer/`, `changesets/20260721-lab3-public-reviewer-gate/`.
- Commits: `68e25c9`, `7130360`, `8c19c0a`, `4dc1c49`, `b97b57e`, `3b4729f`와 최종 마감 commit.
- Public surface: `https://robotics.askewly.com/arm-lab` (접근·검증 2026-07-21).
- Deployment: Vercel `dpl_E8XM8Vzv8uosc18jNBWQwQXdGNsb`, production `READY`, custom alias 연결 PASS.
- Public bundle: `experiments/03-digital-twin/web/assets/arm-lab/registry.json`; registry와 JSON/MP4 12개, 총 13파일의 HTTP 200·byte count·SHA-256 PASS.
- Browser evidence: `experiments/03-digital-twin/web/verify/arm-lab/live-player-report.json`과 `live-desktop-dark.png`, `live-desktop-light.png`, `live-drawer-dark.png`, `live-mobile-dark.png`.
- Live 관측: camera sync delta 0초, graph cursor 동일 frame, console error 0, failed response 0, mobile horizontal overflow 0, fatal 503 recovery PASS.
- Claim gates: 네 event stream 235/661/5/5 events PASS; hidden reasoning, unknown source, recorded/live, simulation/real, camera provenance relabel negative fixture 모두 거부 PASS.
- 크기 회고: 승인 plan의 4개 changeset으로 닫혀 선언한 `changesets>=4`와 일치하며 bundle, player, causal evidence, public reviewer gate가 각각 독립 검증 표면을 가진다.
- C09 배포면 검증: 요구·계획 충족(spec) PASS, 구현 품질(quality) PASS; live QA의 비동기 selector와 strict locator 두 near-miss를 수정 후 재검증했다.
- 정리: 임시 배포 디렉터리는 자동 제거됐고 별도 backend·GPU process·secret 파일을 만들지 않았다.
- 실표면: `https://robotics.askewly.com/arm-lab`에서 desktop dark/light, drawer, mobile, PASS/FAIL, Direct VLA/VLM lane, playback·seek·frame step을 실제 Playwright로 조작해 PASS했다.
- 재현: `cd experiments/03-digital-twin/web; python gen_arm_lab_manifest.py --verify-only; node qa/arm_lab_claim_check.mjs; python qa/arm_lab_player_check.py --url https://robotics.askewly.com/arm-lab --prefix live`.

## 7. 후속 제안 (다음에 무엇을)

첫 후보는 이 공개 화면을 GitHub와 포트폴리오의 대표 진입점으로 연결하고 외부 reviewer가 설명 없이 이해하는지 짧은 관찰 평가를 하는 것이다. 두 번째 후보는 현재 정적 recorded evidence를 유지하면서 task와 object variation을 늘려 일반화 비교 화면으로 확장하는 것이다. 실물 로봇 bring-up은 SO-101 구매·공간·안전 장치가 준비될 때 별도 Horizon으로 열고, 현재 simulation 증거와 섞어 주장하지 않는다.
