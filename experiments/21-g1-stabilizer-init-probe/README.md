# 21-g1-stabilizer-init-probe — G1 walking policy initialization

> M19e. exp18-20에서 reward/reference는 학습되지만 native fall time이 1.24초에 고정된 뒤, 기존 G1 walking policy를 stabilizer prior로 초기화할 수 있는지 확인한다.

## 1. 가설 (Hypothesis)

새 squat policy를 scratch로 학습하면 reward는 올라가도 기본 균형이 없다. 기존 `G1JoystickFlatTerrain` walking policy는 native/browser에서 이미 걷기 안정성을 보였으므로, 같은 네트워크 shape로 squat/reference env를 학습하고 walking params를 `restore_params`로 주입하면 native fall time이 개선될 수 있다.

반증 기준:
- walking params와 squat env PPO network shape가 맞지 않는다.
- Brax PPO `restore_params` fine-tune이 실행되지 않는다.
- native diagnostic fall time이 exp18-20 baseline 1.24초 이하로 유지된다.

## 2. 방법 (Method)

### 셋업
- source params: `/home/yusun/playground-go1/runs/g1flat/params.pkl`.
- 기반 env: exp20 `G1SquatReference`.
- 차이: network shape를 G1 walking default `(512, 256, 128)`로 맞추고 `restore_params`를 사용한다.

### 시나리오
- S1: params shape compatibility probe.
- S2: restored PPO smoke.
- S3: saved params native MuJoCo diagnostic.

### 측정 metric
- policy layer shapes
- restored PPO reward curve
- native `fell_at`, `upright_s`, `min_height`, `max_reference_error`, `energy_proxy`

## 3. 결과 (Results)

### 데이터
| Run | Verdict | Cost | Retries | 비고 |
|-----|---------|------|---------|------|
| S1 shape compatibility | PASS | local WSL/JAX | 0 | walking policy and target policy shapes both `103→512→256→128→58` |
| S2 restored PPO smoke | PASS | 200k target / 204800 eval steps / 5.23min | 1 | eval reward 66.085 -> 66.124 |
| S3 native diagnostic | PASS_DIAGNOSTIC | 6.0s native MuJoCo | 1 | no fall, min height 0.752, max reference error 0.00660, max height error 0.01898 |

### 박제 위치
- `verify/g1-stabilizer-init-probe.json`
- `verify/native-eval.log`
- `verify/train/rewards.txt`

## 4. 통찰 (Insights)

### 무엇을 알아냈나
- 기존 G1 walking policy params는 squat/reference env와 같은 obs/action 차원이고, network shape를 `(512, 256, 128)`로 맞추면 `restore_params` fine-tune이 가능하다.
- stabilizer init은 native fall 병목을 처음으로 깼다. exp18-20은 모두 1.24초에 fall했지만, exp21은 6초 diagnostic에서 no-fall이다.
- 다만 이 결과는 "스쿼트를 성공했다"가 아니다. base height는 0.752~0.758m 근처에 머물러 reference target의 최저 0.62m까지 내려가지 않았다. 즉 stabilizer prior가 넘어짐은 막았지만 squat depth tracking은 약하다.

### 가설은 통과했나?
- [x] PASS — walking stabilizer init이 native fall time을 개선했다.
- [ ] FAIL — walking stabilizer init도 native fall time을 개선하지 못했다.

### 정의에 반영
- `ROADMAP.md` M19를 "stabilizer init no-fall PASS / squat depth pending"으로 갱신한다. 다음 단계는 안정성을 유지한 채 height/reference tracking을 강화하는 fine-tune이다.

### 다음 실험 후보
- walking init을 유지하고 height/reference reward를 더 강하게 주는 longer fine-tune.
- stabilizer frozen/slow-learning layer와 squat head 또는 curriculum을 분리하는 실험.
- browser playback은 no-fall은 가능하지만, "squat skill"로 보이려면 height drop이 native에서 확인된 뒤 진행한다.
