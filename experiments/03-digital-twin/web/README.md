# 디지털 트윈 — 브라우저 임베디먼트 갤러리 (MuJoCo WASM)

로봇 MJCF를 **브라우저에서 실제 물리째** 돌리는 인터랙티브 트윈. DeepMind 공식 MuJoCo WASM
바인딩(`mujoco-js`) + three.js. 빌드·node_modules 불필요 — deps는 jsDelivr CDN, ES module 직접 로드(순수 정적).
하나의 config-driven 하네스(`experiments.json` + `assets/scenes/manifest.json`)로 **11개 씬**을 굴린다.

**라이브: https://physical-ai-arm.askewly.com** (`?exp=<name>` 으로 전환)

| `?exp=` | 임베디먼트 | 구동 |
|---|---|---|
| `go1-walk` | Unitree Go1 (4족) | ⭐ **직접 학습한 RL 정책** live closed-loop (onnxruntime-web) + 조이스틱 조향 |
| `g1-walk` | Unitree G1 (휴머노이드) | ⭐ **직접 학습한 RL 정책** live closed-loop (103-d obs + gait phase clock) |
| `spot-walk` | Boston Dynamics Spot (4족) | ⭐ **직접 학습한 RL 정책** live closed-loop (81-d obs + qpos error history) |
| `g1-rough-walk` | Unitree G1 rough curb | ⭐ **정책 확장 QA** — gait phase humanoid policy + 1/2/3cm curb |
| `go1-rough-walk` · `spot-rough-walk` | Go1 · Spot rough curb | ⭐ **명령·지형 강건성 QA** — 1/2/3cm curb + command sweep |
| `so100-stack` (기본) | SO-ARM100 팔 | scripted pick-and-place 3단 스택 replay |
| `panda-sweep` | Franka Panda 팔 | scripted 관절 sweep replay |
| `shadow-hand` | Shadow Hand | scripted 손가락 굴곡 replay |
| `spot-stand` | Boston Dynamics Spot | 물리 settle (floating-base) |
| `g1-stand` | Unitree G1 | 물리 settle (floating-base 29-DOF) |
| `humanoid-settle` | Humanoid | 물리 settle |
| `dummy-arm` | Dummy 2-link arm | M10 zero-code add 검증용 replay |

- **정책 실험**(go1/g1/spot-walk): `obs→onnx→ctrl→mj_step@50Hz` closed-loop — 학습한 신경망이 실시간으로 몸을 제어한다. 학습 sim과 obs byte-parity. → [exp 04](../../04-go1-rl-walk/README.md)·[05](../../05-g1-rl-walk/README.md)·[06](../../06-spot-rl-walk/README.md).
- **replay 실험**: 데스크탑에서 기록한 qpos 궤적을 운동학 재생(mp4==웹). 시점 궤도/드래그로 직접 구동도 가능.
- **새 임베디먼트 추가 = JS 0줄**: 씬 번들 + `experiments.json` 한 항목 + 궤적/정책. 로더는 `manifest.json`을 fetch.
- 반응형(QHD/노트북/모바일) · 자동 시각 QA 하네스(`qa/visual_check.mjs`, playwright)로 라이브 자가검증.

## 로컬 실행

```bash
python serve_coi.py 8132    # COOP/COEP 헤더 필요 (WASM). deps는 CDN이라 install 불필요
# http://127.0.0.1:8132/index.html
```

> 일반 정적 서버(`python -m http.server`)로는 안 됨 — MuJoCo WASM이 cross-origin isolation
> (COOP `same-origin` + COEP `require-corp`)을 요구한다. `serve_coi.py`가 그 헤더를 붙인다.
> three/mujoco-js는 jsDelivr CDN에서 로드되므로 인터넷 필요(install·node_modules 없음).
> `package.json`은 버전 고정 기록용(CDN URL의 버전과 일치).

## 배포 (Vercel)

순수 정적 — 빌드 없음. [`vercel.json`](vercel.json)이 COOP/COEP 헤더만 설정. `web/`를 루트로 올리면 끝.
(이 레포는 REST API 직접 업로드로 배포: [`deploy_vercel.py`](deploy_vercel.py), `VERCEL_TOKEN` env 필요.)

> **데이터 단일 소스**: `experiments.json`·궤적 JSON의 canonical 사본은 `03/` 루트(파이썬 툴링이 읽고 씀). `web/`는 파생 — 직접 편집하지 말고 `03/`에서 고친 뒤 `python ../sync_web.py`로 미러. `deploy_vercel.py`가 업로드 전 자동 sync하므로 프로덕션은 항상 최신.

## upstream 대비 변경

베이스: [zalo/mujoco_wasm](https://github.com/zalo/mujoco_wasm) (ISC). 주요 delta:
1. `src/mujocoUtils.js` — 씬 파일 목록을 `manifest.json` fetch로(하드코딩 제거), 바이너리 확장자 대소문자 무관 로드.
2. `src/main.js` — `experiments.json` 레지스트리로 씬·카메라 선택, **정책 closed-loop**(onnxruntime-web obs builder + gait phase clock / qpos error history) vs 궤적 replay 2모드, 반응형 카메라.
3. `index.html` — 모바일 컨트롤 패널 축소 CSS.

추가: `assets/scenes/<model>/`(Menagerie 모델 + 우리 scene xml), `gen_scene_manifest.py`(manifest 생성), `decimate_meshes.py`(웹 전송 예산), `qa/`(자동 시각 QA). 학습 정책은 [exp 04](../../04-go1-rl-walk/README.md)·[05](../../05-g1-rl-walk/README.md)·[06](../../06-spot-rl-walk/README.md)에서 ONNX로 뽑아 번들.

## 출처 / 라이선스

- 엔진/뷰어: [zalo/mujoco_wasm](https://github.com/zalo/mujoco_wasm) (ISC), [mujoco-js](https://www.npmjs.com/package/mujoco-js)(DeepMind 공식 WASM 바인딩), [three.js](https://threejs.org) (MIT)
- 모델: [mujoco_menagerie](https://github.com/google-deepmind/mujoco_menagerie) — trs_so_arm100·unitree_go1·unitree_g1·boston_dynamics_spot·franka_emika_panda·shadow_hand 등 (각 모델 라이선스는 해당 디렉터리 참조)
- 학습 정책: [MuJoCo Playground](https://github.com/google-deepmind/mujoco_playground) (Apache-2.0)에서 직접 PPO 학습 → ONNX
- 상위 실험: [../README.md](../README.md) · 결정: [ADR 0004](../../../docs/adr/0004-digital-twin-stack.md)
