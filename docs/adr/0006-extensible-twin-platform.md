# 0006 — 확장 가능한 트윈 플랫폼: 단일 소스 config + 한 커맨드 파이프라인 + 메시 가드 (M10)

- Status: Accepted (2026-06-15)
- 근거 reference: 자체 M8/M9 dogfooding 박제 함정(experiments.json 이중화, manifest 수동 재생성, fast_simplification non-watertight 붕괴), trimesh `is_watertight`, Vercel 정적 배포(빌드 없음)
- 관련: [[0005-learned-policy-sandbox]] config-driven 하네스를 *플랫폼*으로 격상. [[0004-digital-twin-stack]] 웹 번들 구조 연장. M10 step 1~4.

## Context

M8/M9에서 트윈은 config-driven 하네스(`experiments.json` + `harness.py`)가 됐지만, 새 임베디먼트 추가에
**박제된 마찰**이 여럿 남았다(핸드오프 기록):

1. **experiments.json 이중화** — `03/`(파이썬 툴링이 읽음) + `web/`(앱이 fetch)을 수동 `cp`로 동기화. 한쪽만
   고치면 조용히 깨진다(M9에서도 teleop 플래그를 둘 다 편집 후 cp).
2. **수동 manifest 재생성** — 씬 추가 후 `gen_scene_manifest.py`를 손으로 돌려야 웹 로더가 파일을 인식.
3. **메시 변환 비자명** — `fast_simplification`이 **non-watertight(열린 shell, 예: Franka panda)** 메시를
   파편화시킨다. 사람이 "이건 감축하지 말 것"을 기억해야 했다.

목표(사용자 방향): **문서만 보고 새 임베디먼트 1종을 bespoke 코드 0줄로 추가**. 마찰을 사람의 기억이 아니라
코드·문서가 막게 한다.

## Decision

**M10에서 세 가지 메커니즘으로 마찰을 코드화한다.**

1. **experiments.json 단일 소스화 = 복사 스크립트 + 배포 가드** (심볼릭/제자리-canonical 아님).
   - `03/` 루트를 canonical(파이썬 툴링의 read/write 위치), `web/`는 파생. `sync_web.py`가 03/ 루트 모든
     `*.json`을 web/로 멱등 복사(자동 발견 → 새 궤적 누락 불가). `--check`는 stale 시 exit 1.
   - `deploy_vercel.py`가 업로드 전 sync를 자동 실행 → **프로덕션이 stale 사본을 배포하는 것이 구조적으로 불가능**.
   - **왜 심볼릭 아님**: Windows 심볼릭·Vercel 정적 업로드가 링크를 안 따라갈 위험. **왜 web/-canonical 아님**:
     파이썬 툴링 경로를 전부 retarget해야 해 변경 범위가 큼. 복사 스크립트가 최소 변경 + Windows/Vercel 안전.
2. **씬 추가 파이프라인 일원화 = `add_scene.sh` 한 커맨드.**
   - `decimate→manifest→record→smoke→loadtest→render→sync→visual`을 fail-fast로 한 번에. 모든 step은
     `experiments.json`(harness.py) 구동 — 임베디먼트별 하드코딩 0. 3개 런타임(Windows python·node·WSL venv)을
     한 드라이버에서 조율(WSL 경로는 `/c/`→`/mnt/c/` sed 변환으로 trap 회피).
3. **메시 변환 watertight 가드 = `decimate_meshes.py`가 `is_watertight`로 자동 분기.**
   - watertight만 simplify, **non-watertight는 KEPT(무감축, wasm 로더 호환 위해 재export만)**, 150k면 초과 시 WARN.
   - **왜 코드가 막나**: 함정 #1은 "사람이 조심"으로는 재발한다. 판정을 코드에 박아 예방.

검증(완료 기준): 더미 임베디먼트 `dummy-arm`(self-contained primitives MJCF + 레지스트리 1항목, 파이프라인
코드 0줄)을 `add_scene.sh dummy-arm --record` 한 커맨드로 갤러리 추가 → 전 게이트 PASS, 라이브. 가이드:
[`ADDING_EMBODIMENTS.md`](../../experiments/03-digital-twin/ADDING_EMBODIMENTS.md).

## Consequences

- **(+)** 박제 함정 #1·#2·#4(non-watertight 붕괴·json 이중화·manifest 누락)가 "사람이 조심"에서 "코드가 막음"으로 전환.
- **(+)** "도구"가 "플랫폼"으로 — M11(Spot)이 이 위에서 dogfood돼 정책 1종을 저마찰로 흡수(실증됨).
- **(+)** UI에 갤러리 셀렉터가 없어 `?exp=`로만 노출 → 더미/검증용 임베디먼트를 쇼케이스 오염 없이 올릴 수 있다.
- **(−)** `add_scene.sh`가 3개 런타임을 가정(Windows python·node·WSL venv) — 다른 환경에선 경로 가정 수정 필요.
- **(−)** 복사 스크립트는 "한 번 실행"을 요구(심볼릭처럼 자동 아님). 배포 가드로 프로덕션은 막지만, 로컬 QA를
  stale 사본으로 돌릴 여지는 남음(`--check`로 완화).
- **되돌림 조건**: 임베디먼트가 수십 종으로 늘어 복사 스크립트·플랫 03/ 레이아웃이 한계에 닿으면, 빌드 단계
  도입(번들러) + web/-canonical 재검토. 현재 규모(~10종)에선 과설계.
