# references/

분석한 외부 레포·자료의 인덱스. 클론은 이 폴더 안에만(루트에 stray repo 금지).

각 분석 노트는 `<handle>-<repo>/ANALYSIS.md` 5섹션 형식 — 템플릿: [ANALYSIS_TEMPLATE.md](ANALYSIS_TEMPLATE.md).

## 인덱스

| # | 레포 | 분석일 | 한 줄 요약 | 5섹션 완료 | 정의 반영 |
|---|------|--------|-----------|------------|----------|
| 1 | openvla/openvla | 2026-06-09 | 오픈소스 7B VLA — VLM(Prismatic) + 이산 동작 토큰화 | ✅ 5/5 | [ADR 0001](../docs/adr/0001-vla-action-representation.md) |
| 2 | Physical-Intelligence/openpi (π0) | 2026-06-09 | flow matching VLA — PaliGemma + action expert | ✅ 5/5 | [ADR 0001](../docs/adr/0001-vla-action-representation.md) |
| 3 | tonyzhaozh/act (ALOHA+ACT) | 2026-06-09 | 저가 양팔 HW + CVAE action chunking 회귀 | ✅ 5/5 | [ADR 0001](../docs/adr/0001-vla-action-representation.md) |
| 4 | google-deepmind/open_x_embodiment | 2026-06-09 | RLDS 통합 데이터셋 + cross-embodiment RT-X | ✅ 5/5 | [ADR 0001](../docs/adr/0001-vla-action-representation.md) |
| 5 | VLA 서베이 (arxiv 2508.13073) | 2026-06-09 | monolithic/hierarchical taxonomy (논문, 클론 X) | ✅ 5/5 | [ADR 0001](../docs/adr/0001-vla-action-representation.md) |
| 6 | rerun-io/rerun | 2026-07-20 | 멀티모달 로봇 데이터의 실시간·episode 관찰 하네스 | ✅ 5/5 | LAB1 내부 증거 뷰어 후보 |
| 7 | huggingface/lerobot | 2026-07-20 | 로봇 실행·데이터·정책 + Rerun/Foxglove 관찰 경로 | ✅ 5/5 | LAB1 기준선 |
| 8 | huggingface/lerobot-dataset-visualizer | 2026-07-20 | 복수 camera·action graph·언어 annotation 동기 웹앱 | ✅ 5/5 | LAB3 UI 기준선 |
| 9 | nicolas-rabault/leLab | 2026-07-20 | LeRobot 실물 운영 FastAPI backend | ✅ 5/5 | 실물 단계 UX 참고 |
| 10 | jurmy24/leLab-space | 2026-07-20 | camera·URDF·replay·training UI shell | ✅ 5/5 | placeholder 경계 참고 |
| 11 | huangwl18/VoxPoser | 2026-07-20 | 언어→3D value map→trajectory의 계층형 조작 | ✅ 5/5 | LAB2 판단 시각화 참고 |
| 12 | 2419924948gyt/RoboVLA-Workbench | 2026-07-20 | symbolic plan + 2D PNG replay 교육 prototype | ✅ 5/5 | negative reference |

## 분석 원칙
- 시간 박스: 레포당 90분
- 5섹션 다 채우기 전엔 정의 갱신·통찰 보고 금지
- 인용은 출처 URL + 접근일 필수
