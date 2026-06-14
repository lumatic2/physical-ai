# 새 임베디먼트 / 정책 추가 — N단계

> M10(확장 가능한 트윈 플랫폼)의 운영 가이드. **목표: 파이프라인 코드(.py/.js/.sh)를 한 줄도 고치지 않고**
> 데이터(씬 MJCF) + 설정(`experiments.json` 한 항목) + 궤적만으로 새 임베디먼트를 갤러리에 올린다.
> 한 커맨드 `add_scene.sh` 가 체인 전체(manifest→record→smoke→loadtest→render→sync→visual)를 fail-fast로 돈다.

핵심 단일 소스는 `experiments.json`(03/ 루트 = canonical, `web/`는 파생). harness(`harness.py`)가 이 레지스트리
하나로 모든 도구를 구동하므로, 임베디먼트별 분기 코드가 없다.

---

## 1) 씬 번들 — `web/assets/scenes/<model>/`

두 경로 중 하나:

- **Menagerie 모델**: sparse-checkout 후 모델 폴더를 `web/assets/scenes/<model>/` 로 복사
  (`setup.sh` 의 `trs_so_arm100` 패턴 참조). 메시(`.stl`/`.obj`)는 그대로 들어간다 → 2)에서 감축.
- **Self-contained MJCF**: 메시 없이 primitives 로만 짠 씬(예시: `dummy/scene_dummy.xml`). 메시 전송 예산·감축이
  필요 없어 가장 빠르다.

> ⚠ **wasm 0.0.7 strict** (박제 함정 #4): 웹 로더(mujoco-js 0.0.7)는 데스크톱 MuJoCo보다 엄격하다.
> primitives(`box`/`capsule`/`sphere`/`cylinder`/`plane`)·builtin texture·`motor` 액추에이터는 안전.
> Meshlab-authored `.obj` 일부는 로드 실패 → 2)의 trimesh 재export가 정규화해준다. 의심되면 5)의
> `loadtest` 가 체인 안에서 선검증한다.

## 2) (메시가 있으면) 감축 — `add_scene.sh <exp> --decimate <model>`

`web/assets/scenes/<model>/assets/` 의 메시를 웹 예산까지 감축한다. **WSL venv**(`trimesh`+`fast_simplification`)에서
돈다 — `add_scene.sh` 가 경로를 `/mnt/...` 로 변환해 호출한다.

> ⚠ **watertight 가드** (박제 함정 #1, M10 step3에서 코드화): `decimate_meshes.py` 가 `is_watertight` 로 자동 분기.
> watertight 메시만 simplify, **non-watertight(열린 shell — Franka panda 류)은 무감축으로 KEPT**(simplify하면 파편화).
> 150k면 초과 non-watertight 는 `WARN` — 손으로 줄여야 한다. 즉 함정을 코드가 막으므로 사용자가 신경 쓸 필요 없다.

self-contained primitives 씬(메시 0개)이면 이 단계는 생략한다.

## 3) `experiments.json` 항목 추가 (03/ 루트 = canonical)

```jsonc
"<exp-name>": {
  "title": "...",                         // 한국어 설명
  "scene": "<model>/scene_<model>.xml",   // assets/scenes/ 기준 상대경로
  "trajectory": "<name>_trajectory.json",  // 4)에서 생성
  "ee_body": "<body>",                     // smoke FK·EE 텔레옵 기준 바디
  "render_out": "media/<name>.mp4",
  "camera": { "lookat": [..], "distance": .., "azimuth": .., "elevation": .. },  // 데스크톱 mp4
  "web":    { "target": [..], "offset": [.., .., ..], "fovDist": 1.0 }            // 웹 카메라
  // 학습 정책 씬이면 추가로 "policy": { onnx, obs_layout, gait, ... } — exp 04/05 참조
  // 고정팔 EE 텔레옵을 켜려면 "teleop": true
}
```

`web/experiments.json` 은 **건드리지 않는다** — 5)의 sync 가 03/ 에서 미러한다(박제 함정 #2, M10 step1).

## 4) 궤적 생성 — 임베디먼트 성격에 맞게

- **generic(물리 settle/drop)** → 코드 0줄: `add_scene.sh <exp> --record` (내부적으로 `record_trajectory.py`).
- **scripted(pick-and-place 등)** → `make_pick_trajectory.py` 류 전용 생성기.
- **학습 정책(ONNX closed-loop)** → `rollout_g1.py` / `rollout_policy.py` 로 궤적·obs 박제(exp 04/05 파이프라인).

## 5) 한 커맨드 — `add_scene.sh`

```bash
bash add_scene.sh <exp> [--record] [--decimate <model>] [--skip-render] [--skip-qa]
```

순서대로 fail-fast: `decimate?` → `manifest` → `record?` → `smoke`(헤드리스 로드 게이트) →
`loadtest`(wasm 선검증) → `render`(mp4) → `sync`(web/ 미러) → `visual`(헤드리스 브라우저 QA + 스크린샷).
하나라도 비정상 종료하면 중단된다.

## 6) 배포

```bash
python web/deploy_vercel.py     # 업로드 전 sync_web.py 자동 선행 → 프로덕션은 항상 최신
```

라이브에서 `?exp=<exp-name>` 으로 확인. (UI에 갤러리 셀렉터가 없어, 등록만 하면 default 외에는
`?exp=` 로만 노출된다 — 데모용/검증용 임베디먼트를 쇼케이스 오염 없이 올릴 수 있다.)

---

## 워크드 예시 — `dummy-arm` (이 레포에 포함, 로컬 QA PASS; 배포 시 `?exp=dummy-arm`)

M10 완료 검증으로 추가한 **2링크 더미 팔**. 파이프라인 코드 0줄, 데이터만으로 추가:

1. 씬: [`web/assets/scenes/dummy/scene_dummy.xml`](web/assets/scenes/dummy/scene_dummy.xml) — primitives만(메시 0개),
   ee_body=`tip`, `home` 키프레임 1개.
2. 항목: `experiments.json` 에 `dummy-arm` (위 3)의 스키마, policy 없음 → replay).
3. 한 커맨드:
   ```bash
   bash add_scene.sh dummy-arm --record
   ```
   실제 출력:
   ```
   SMOKE PASS                         (tip 이동 |delta|=0.39)
   WASM OK nq= 2 nu= 2                 (wasm 선검증)
   render dummy_arm.mp4: 90 frames
   sync: dummy_arm_trajectory.json, experiments.json synced
   [qa] PASS ✅  (replay, consoleErrors 0)
   == DONE
   ```

메시 있는 실모델이면 1)에서 sparse-checkout + `--decimate <model>` 만 추가하면 동일하게 0줄.

---

## 박제 함정 → 코드화 상태 (M9 핸드오프 대비)

| 함정 | 과거(수동) | 지금(코드가 막음) |
|---|---|---|
| experiments.json 이중화 | 03/ + web/ 수동 `cp` | `sync_web.py` 자동 + 배포 가드 (M10 s1) |
| manifest 재생성 누락 | 수동 `gen_scene_manifest.py` | `add_scene.sh` 가 자동 (M10 s2) |
| fast_simplification non-watertight 붕괴 | 사람이 조심 | `is_watertight` 가드 자동 KEPT (M10 s3) |
| wasm 0.0.7 로드 실패 | 배포 후 발견 | `loadtest` 가 체인 안에서 선검증 |
| WSL 경로 치환 깨짐 | 리터럴 손수 | `add_scene.sh` 가 `/c/`→`/mnt/c/` sed 변환 |
