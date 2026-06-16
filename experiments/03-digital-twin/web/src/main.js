
import * as THREE           from 'three';
import { GUI              } from 'three/addons/libs/lil-gui.module.min.js';
import { OrbitControls    } from 'three/addons/controls/OrbitControls.js';
import { DragStateManager } from './utils/DragStateManager.js';
import { setupGUI, downloadExampleScenesFolder, loadSceneFromURL, drawTendonsAndFlex, getPosition, getQuaternion, toMujocoPos, standardNormal } from './mujocoUtils.js';
import   load_mujoco        from 'https://cdn.jsdelivr.net/npm/mujoco-js@0.0.7/dist/mujoco_wasm.js';

// Load the MuJoCo Module
const mujoco = await load_mujoco();

// Set up Emscripten's Virtual File System
var initialScene = "humanoid.xml";
mujoco.FS.mkdir('/working');
mujoco.FS.mount(mujoco.MEMFS, { root: '.' }, '/working');
mujoco.FS.writeFile("/working/" + initialScene, await(await fetch("./assets/scenes/" + initialScene)).text());

export class MuJoCoDemo {
  constructor() {
    this.mujoco = mujoco;

    // Load in the state from XML
    this.model = mujoco.MjModel.loadFromXML("/working/" + initialScene);
    this.data  = new mujoco.MjData(this.model);

    // Define Random State Variables
    this.params = { scene: initialScene, paused: false, help: false, ctrlnoiserate: 0.0, ctrlnoisestd: 0.0, keyframeNumber: 0, replay: true };
    this.mujoco_time = 0.0;
    this.bodies  = {}, this.lights = {};
    this.tmpVec  = new THREE.Vector3();
    this.tmpQuat = new THREE.Quaternion();
    this.updateGUICallbacks = [];

    this.container = document.createElement( 'div' );
    document.body.appendChild( this.container );

    this.scene = new THREE.Scene();
    this.scene.name = 'scene';

    this.camera = new THREE.PerspectiveCamera( 45, window.innerWidth / window.innerHeight, 0.001, 100 );
    this.camera.name = 'PerspectiveCamera';
    // Frame the SO-100 + the pick-and-place workspace (start blocks -> stack pad). Orbit
    // around the workspace centroid (not the base) so the stacking action isn't cut off at
    // the bottom edge. Pull back on portrait/narrow viewports (phones) so it still fits —
    // three.js fov is vertical, so narrow aspect crops horizontally.
    this.viewTarget = new THREE.Vector3(0.10, 0.06, 0.13);
    {
      const aspect = window.innerWidth / window.innerHeight;
      const dist = 1.0 * Math.max(1, 1.0 / aspect);
      this.camera.position.set(
        this.viewTarget.x + 0.52 * dist,
        this.viewTarget.y + 0.42 * dist,
        this.viewTarget.z + 0.52 * dist);
    }
    this.scene.add(this.camera);

    this.scene.background = new THREE.Color(0.15, 0.25, 0.35);
    this.scene.fog = new THREE.Fog(this.scene.background, 15, 25.5 );

    this.ambientLight = new THREE.AmbientLight( 0xffffff, 0.1 * 3.14 );
    this.ambientLight.name = 'AmbientLight';
    this.scene.add( this.ambientLight );

    this.spotlight = new THREE.SpotLight();
    this.spotlight.angle = 1.11;
    this.spotlight.distance = 10000;
    this.spotlight.penumbra = 0.5;
    this.spotlight.castShadow = true; // default false
    this.spotlight.intensity = this.spotlight.intensity * 3.14 * 10.0;
    this.spotlight.shadow.mapSize.width = 1024; // default
    this.spotlight.shadow.mapSize.height = 1024; // default
    this.spotlight.shadow.camera.near = 0.1; // default
    this.spotlight.shadow.camera.far = 100; // default
    this.spotlight.position.set(0, 3, 3);
    const targetObject = new THREE.Object3D();
    this.scene.add(targetObject);
    this.spotlight.target = targetObject;
    targetObject.position.set(0, 1, 0);
    this.scene.add( this.spotlight );

    this.renderer = new THREE.WebGLRenderer( { antialias: true } );
    this.renderer.setPixelRatio(1.0);////window.devicePixelRatio );
    this.renderer.setSize( window.innerWidth, window.innerHeight );
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap; // default THREE.PCFShadowMap
    THREE.ColorManagement.enabled = false;
    this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    //this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
    //this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    //this.renderer.toneMappingExposure = 2.0;
    this.renderer.useLegacyLights = true;

    this.renderer.setAnimationLoop( this.render.bind(this) );

    this.container.appendChild( this.renderer.domElement );

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.target.copy(this.viewTarget); // orbit the pick-and-place workspace
    this.controls.panSpeed = 2;
    this.controls.zoomSpeed = 1;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.10;
    this.controls.screenSpacePanning = true;
    this.controls.update();

    window.addEventListener('resize', this.onWindowResize.bind(this));

    // Initialize the Drag State Manager.
    this.dragStateManager = new DragStateManager(this.scene, this.renderer, this.camera, this.container.parentElement, this.controls);
  }

  async init() {
    // Download the the examples to MuJoCo's virtual file system
    await downloadExampleScenesFolder(mujoco);

    // Harness: pick the experiment from experiments.json (default, or ?exp= override).
    // Each experiment = (scene MJCF, recorded trajectory, camera) — same registry the
    // desktop smoke/render/record read. Default stays SO-100 so the live site is unchanged.
    const registry = await (await fetch("./experiments.json")).json();
    const expName = new URLSearchParams(location.search).get("exp") || registry.default;
    const exp = registry.experiments[expName] || registry.experiments[registry.default];
    this.registry = registry;
    this.expName = registry.experiments[expName] ? expName : registry.default;
    this.exp = exp;

    const startScene = exp.scene;
    this.params.scene = startScene;
    [this.model, this.data, this.bodies, this.lights] =
      await loadSceneFromURL(mujoco, startScene, this);

    // Frame the camera from the experiment config (workspace centroid + pull-back offset,
    // scaled on narrow/portrait viewports since three.js fov is vertical).
    const w = exp.web;
    this.viewTarget.set(w.target[0], w.target[1], w.target[2]);
    const aspect = window.innerWidth / window.innerHeight;
    const dist = w.fovDist * Math.max(1, 1.0 / aspect);
    this.camera.position.set(
      this.viewTarget.x + w.offset[0] * dist,
      this.viewTarget.y + w.offset[1] * dist,
      this.viewTarget.z + w.offset[2] * dist);
    this.controls.target.copy(this.viewTarget);
    this.controls.update();

    // Two rollout modes:
    //  (A) policy block -> LIVE closed-loop inference (obs -> onnx -> ctrl -> mj_step). A
    //      learned neural net drives the sim in real time in the browser.
    //  (B) trajectory   -> kinematic replay (set qpos + mj_forward), matches desktop mp4.
    this.policy = exp.policy || null;
    if (this.policy) {
      await this.initPolicy();
      this.gui = new GUI();
      setupGUI(this);
      this.addCommandGUI();
    } else {
      // (B) replay: NOTE the 'home' keyframe may pad free-joints to the origin, so we
      // seed from trajectory frame 0.
      const traj = await (await fetch("./" + exp.trajectory)).json();
      this.replayFps = traj.fps;
      this.replayQpos = traj.qpos;            // [frame][nq]
      this.replayN = traj.qpos.length;
      this.replayStartMS = null;
      this.seedFrame(0);

      this.gui = new GUI();
      setupGUI(this);
      // Replay toggle — default on. Off hands control back to physics + drag.
      this.replayToggle = this.gui.add(this.params, 'replay').name('▶ Replay (grab to take over)').onChange((v) => {
        this.replayStartMS = null;
        if (!v) { this.seedFrame(0); }
      });
      // (C) EE teleop for fixed-base arms (experiments.json `teleop: true`).
      this.teleopCfg = exp.teleop ? { ee_body: exp.ee_body } : null;
      if (this.teleopCfg) { this.initTeleop(); }
    }

    this.addControlHints();
    this.addProjectOverlay();
  }

  addProjectOverlay() {
    const groups = [
      ['policy', 'Walking policies', ['g1-walk', 'barkour-walk', 'go1-walk', 'spot-walk', 'g1-rough-walk', 'go1-rough-walk', 'spot-rough-walk']],
      ['skills', 'Humanoid skills', ['g1-controlled-squat']],
      ['manipulation', 'Arms and hands', ['so100-stack', 'panda-sweep', 'shadow-hand', 'dummy-arm']],
      ['checks', 'Model checks', ['g1-stand', 'spot-stand', 'humanoid-settle']],
    ];
    const experimentCopy = {
      'g1-walk': {
        name: 'Unitree G1',
        kind: 'Humanoid walking',
        description: 'A full-body humanoid policy running closed-loop in the browser.',
        actions: ['Walk forward', 'Strafe', 'Turn', 'Push and recover'],
        learned: 'Joystick-conditioned balance and locomotion policy.',
      },
      'g1-rough-walk': {
        name: 'Unitree G1 Rough',
        kind: 'Humanoid terrain',
        description: 'The G1 walking policy tested on low curb terrain.',
        actions: ['Walk over curbs', 'Turn', 'Command sweep'],
        learned: 'Same G1 gait policy checked against rough-terrain robustness.',
      },
      'g1-controlled-squat': {
        name: 'Unitree G1 Lowering Probe',
        kind: 'Humanoid balance probe',
        description: 'A shallow lowering replay from the M19 controller audit. It is stable, but not a visible squat.',
        actions: ['Balance', 'Lower slightly', 'Return upright'],
        learned: 'Stabilizer policy plus calibrated reference controller; visible squat gate remains open.',
      },
      'barkour-walk': {
        name: 'Google Barkour',
        kind: 'Quadruped walking',
        description: 'A compact quadruped policy with observation history.',
        actions: ['Walk forward', 'Strafe', 'Turn'],
        learned: 'History-based joystick locomotion policy.',
      },
      'go1-walk': {
        name: 'Unitree Go1',
        kind: 'Quadruped walking',
        description: 'A four-legged robot policy running directly in WebAssembly.',
        actions: ['Walk forward', 'Strafe', 'Turn', 'Drag test'],
        learned: 'Joystick locomotion policy exported to ONNX.',
      },
      'go1-rough-walk': {
        name: 'Unitree Go1 Rough',
        kind: 'Quadruped terrain',
        description: 'Go1 locomotion checked on rough curb scenes.',
        actions: ['Walk over curbs', 'Command sweep', 'Drag test'],
        learned: 'Go1 policy reused for terrain robustness checks.',
      },
      'spot-walk': {
        name: 'Boston Dynamics Spot',
        kind: 'Quadruped walking',
        description: 'A Spot model driven by a live closed-loop policy.',
        actions: ['Walk forward', 'Strafe', 'Turn', 'Drag test'],
        learned: 'Joystick locomotion with short motion history.',
      },
      'spot-rough-walk': {
        name: 'Spot Rough',
        kind: 'Quadruped terrain',
        description: 'Spot policy tested against curb terrain and command changes.',
        actions: ['Walk over curbs', 'Command sweep', 'Drag test'],
        learned: 'Terrain robustness check for the Spot walking policy.',
      },
      'so100-stack': {
        name: 'SO-100',
        kind: 'Robot arm',
        description: 'A low-cost arm digital twin replaying a three-block pick-and-place task.',
        actions: ['Replay stack', 'Drag objects', 'Teleop gripper'],
        learned: 'Scripted trajectory and teleop harness; not a learned policy.',
      },
      'panda-sweep': {
        name: 'Franka Panda',
        kind: 'Robot arm',
        description: 'A 7-DOF arm scene for joint motion and teleop checks.',
        actions: ['Replay joint sweep', 'Teleop end-effector'],
        learned: 'Control and visualization baseline for arm embodiments.',
      },
      'shadow-hand': {
        name: 'Shadow Hand',
        kind: 'Dexterous hand',
        description: 'A hand model replaying finger flexion and contact-ready motion.',
        actions: ['Replay finger curl', 'Inspect joints'],
        learned: 'Dexterous-hand scene and replay baseline.',
      },
      'dummy-arm': {
        name: 'Dummy 2-link arm',
        kind: 'Harness check',
        description: 'A small test arm used to prove new scenes can be added cleanly.',
        actions: ['Replay motion', 'Scene loading check'],
        learned: 'Zero-code embodiment addition workflow.',
      },
      'g1-stand': {
        name: 'Unitree G1 Stand',
        kind: 'Model check',
        description: 'The G1 model settling under physics without the walking policy.',
        actions: ['Settle', 'Drag test', 'Inspect posture'],
        learned: 'Baseline model stability check before skill work.',
      },
      'spot-stand': {
        name: 'Spot Stand',
        kind: 'Model check',
        description: 'Spot model settling under physics.',
        actions: ['Settle', 'Drag test'],
        learned: 'Baseline model stability check.',
      },
      'humanoid-settle': {
        name: 'Humanoid',
        kind: 'Model check',
        description: 'A generic humanoid scene used to validate the platform.',
        actions: ['Settle', 'Drag test'],
        learned: 'General MuJoCo loading and replay coverage.',
      },
    };
    const panel = document.createElement('section');
    panel.className = 'project-panel';
    panel.innerHTML = `
      <div class="project-panel__head">
        <div>
          <div class="project-panel__brand">Robotics Lab</div>
          <div class="project-panel__domain">robotics.askewly.com</div>
        </div>
        <button class="project-panel__toggle" type="button" aria-expanded="true" title="Collapse panel">-</button>
      </div>
      <div class="project-panel__body">
        <div class="robot-picker">
          <button class="robot-picker__button" type="button" aria-expanded="false">
            <span>
              <span class="robot-picker__name"></span>
              <span class="robot-picker__kind"></span>
            </span>
            <span class="robot-picker__chevron">v</span>
          </button>
          <div class="robot-picker__menu" role="menu"></div>
        </div>
        <div class="robot-card">
          <div class="robot-card__description"></div>
          <div class="robot-card__section">
            <div class="robot-card__label">Try</div>
            <div class="robot-card__chips robot-card__actions"></div>
          </div>
          <div class="robot-card__section">
            <div class="robot-card__label">What this shows</div>
            <div class="robot-card__learned"></div>
          </div>
        </div>
        <div class="research-card">
          <div class="research-card__label">Current skill work</div>
          <div class="research-card__title">G1 visible squat gate open</div>
          <div class="research-card__text">The current replay is a stable micro-dip, not a finished squat. Next gate: at least 8cm pelvis drop with knee and hip flexion, no fall, and both feet in contact.</div>
        </div>
      </div>
    `;
    const style = document.createElement('style');
    style.textContent = `
      .project-panel {
        position: absolute;
        top: 14px;
        left: 14px;
        z-index: 1200;
        width: min(344px, calc(100vw - 28px));
        color: #f7fbff;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: rgba(8, 12, 16, 0.76);
        border: 1px solid rgba(255,255,255,0.16);
        box-shadow: 0 18px 60px rgba(0,0,0,0.34);
        backdrop-filter: blur(14px);
        border-radius: 8px;
        overflow: hidden;
      }
      .project-panel, .project-panel * { box-sizing: border-box; }
      .project-panel__head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 13px 14px 11px;
        border-bottom: 1px solid rgba(255,255,255,0.12);
      }
      .project-panel__brand {
        font-size: 16px;
        line-height: 1.15;
        font-weight: 700;
      }
      .project-panel__domain {
        margin-top: 3px;
        color: rgba(247,251,255,0.66);
        font-size: 12px;
        line-height: 1.2;
      }
      .project-panel__toggle {
        width: 28px;
        height: 28px;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 6px;
        color: #f7fbff;
        background: rgba(255,255,255,0.08);
        font: 700 16px/1 ui-sans-serif, system-ui, sans-serif;
        cursor: pointer;
      }
      .project-panel__body { padding: 13px 14px 14px; }
      .robot-picker {
        position: relative;
      }
      .robot-picker__button {
        width: 100%;
        min-height: 48px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 6px;
        padding: 8px 10px;
        color: #f7fbff;
        background: rgba(0,0,0,0.42);
        text-align: left;
        cursor: pointer;
      }
      .robot-picker__name {
        display: block;
        font-size: 14px;
        line-height: 1.2;
        font-weight: 750;
      }
      .robot-picker__kind {
        display: block;
        margin-top: 3px;
        color: rgba(247,251,255,0.62);
        font-size: 12px;
        line-height: 1.2;
      }
      .robot-picker__chevron {
        color: rgba(247,251,255,0.7);
        font-size: 13px;
        line-height: 1;
      }
      .robot-picker__menu {
        display: none;
        position: absolute;
        top: calc(100% + 6px);
        left: 0;
        right: 0;
        max-height: min(430px, calc(100vh - 180px));
        overflow: auto;
        padding: 8px;
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 8px;
        background: #081016;
        box-shadow: 0 18px 50px rgba(0,0,0,0.42);
      }
      .robot-picker.is-open .robot-picker__menu { display: block; }
      .robot-picker.is-open ~ .robot-card,
      .robot-picker.is-open ~ .research-card { visibility: hidden; }
      .robot-picker__group {
        margin: 8px 4px 5px;
        color: rgba(247,251,255,0.48);
        font-size: 11px;
        line-height: 1.2;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      .robot-picker__item {
        width: 100%;
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 8px;
        align-items: center;
        min-height: 38px;
        padding: 7px 8px;
        border: 0;
        border-radius: 6px;
        color: #f7fbff;
        background: transparent;
        text-align: left;
        cursor: pointer;
      }
      .robot-picker__item:hover,
      .robot-picker__item.is-active {
        background: rgba(255,255,255,0.10);
      }
      .robot-picker__item-name {
        font-size: 13px;
        line-height: 1.2;
        font-weight: 700;
      }
      .robot-picker__item-kind {
        color: rgba(247,251,255,0.54);
        font-size: 11px;
      }
      .robot-card {
        margin-top: 12px;
        padding: 12px;
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 8px;
        background: rgba(255,255,255,0.045);
      }
      .robot-card__description {
        color: rgba(247,251,255,0.88);
        font-size: 13px;
        line-height: 1.45;
      }
      .robot-card__section {
        margin-top: 11px;
      }
      .robot-card__label,
      .research-card__label {
        margin-bottom: 6px;
        color: rgba(247,251,255,0.54);
        font-size: 11px;
        line-height: 1.2;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }
      .robot-card__chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .robot-card__chip {
        display: inline-flex;
        align-items: center;
        min-height: 24px;
        padding: 0 8px;
        color: #f7fbff;
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 999px;
        background: rgba(255,255,255,0.07);
        font-size: 11px;
        line-height: 1;
      }
      .robot-card__learned,
      .research-card__text {
        color: rgba(247,251,255,0.76);
        font-size: 12px;
        line-height: 1.45;
      }
      .research-card {
        margin-top: 13px;
        padding: 12px;
        border-radius: 8px;
        background: rgba(73, 124, 176, 0.16);
        border: 1px solid rgba(156, 202, 255, 0.18);
      }
      .research-card__title {
        margin-bottom: 5px;
        font-size: 13px;
        line-height: 1.25;
        font-weight: 700;
      }
      .project-panel.is-collapsed .project-panel__body { display: none; }
      .project-panel.is-collapsed { width: auto; min-width: 210px; }
      @media (max-width: 640px) {
        .project-panel {
          top: 8px;
          left: 8px;
          width: calc(100vw - 16px);
        }
        .robot-picker__menu {
          max-height: min(420px, calc(100vh - 150px));
        }
        .research-card { display: none; }
      }
    `;
    document.head.appendChild(style);

    const picker = panel.querySelector('.robot-picker');
    const pickerButton = panel.querySelector('.robot-picker__button');
    const pickerName = panel.querySelector('.robot-picker__name');
    const pickerKind = panel.querySelector('.robot-picker__kind');
    const pickerMenu = panel.querySelector('.robot-picker__menu');
    const description = panel.querySelector('.robot-card__description');
    const actions = panel.querySelector('.robot-card__actions');
    const learned = panel.querySelector('.robot-card__learned');
    const metaFor = (key) => experimentCopy[key] || {
      name: key,
      kind: this.registry.experiments[key]?.policy ? 'Policy' : 'Replay',
      description: this.registry.experiments[key]?.title || key,
      actions: ['Inspect scene'],
      learned: 'Experiment registered in the robot platform.',
    };
    const navigateTo = (key) => {
      const next = new URL(location.href);
      next.searchParams.set('exp', key);
      location.href = next.toString();
    };
    for (const [, label, keys] of groups) {
      const groupLabel = document.createElement('div');
      groupLabel.className = 'robot-picker__group';
      groupLabel.textContent = label;
      pickerMenu.appendChild(groupLabel);
      for (const key of keys) {
        if (!this.registry.experiments[key]) continue;
        const meta = metaFor(key);
        const item = document.createElement('button');
        item.type = 'button';
        item.className = `robot-picker__item${key === this.expName ? ' is-active' : ''}`;
        item.dataset.exp = key;
        item.innerHTML = `
          <span class="robot-picker__item-name">${meta.name}</span>
          <span class="robot-picker__item-kind">${meta.kind}</span>
        `;
        item.addEventListener('click', () => navigateTo(key));
        pickerMenu.appendChild(item);
      }
    }

    const currentMeta = metaFor(this.expName);
    pickerName.textContent = currentMeta.name;
    pickerKind.textContent = currentMeta.kind;
    description.textContent = currentMeta.description;
    learned.textContent = currentMeta.learned;
    for (const action of currentMeta.actions) {
      const chip = document.createElement('span');
      chip.className = 'robot-card__chip';
      chip.textContent = action;
      actions.appendChild(chip);
    }
    pickerButton.addEventListener('click', () => {
      const open = picker.classList.toggle('is-open');
      pickerButton.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('pointerdown', (event) => {
      if (!panel.contains(event.target)) {
        picker.classList.remove('is-open');
        pickerButton.setAttribute('aria-expanded', 'false');
      }
    });
    panel.querySelector('.project-panel__toggle').addEventListener('click', (event) => {
      const button = event.currentTarget;
      const collapsed = panel.classList.toggle('is-collapsed');
      button.textContent = collapsed ? '+' : '-';
      button.setAttribute('aria-expanded', String(!collapsed));
    });
    this.container.appendChild(panel);
  }

  // Always-on control hint (bottom-left). Discoverability for the interactive controls — the
  // teleop only matters if the visitor knows it's there. Embodiment-aware: keyboard-steer line
  // appears only for policy (joystick) experiments; the drag/orbit line is universal. The arm
  // EE-teleop line is added in step 3. pointer-events:none so it never blocks a drag.
  addControlHints() {
    const hint = document.createElement('div');
    hint.style.cssText =
      'position:absolute;left:10px;bottom:10px;color:#fff;font:13px/1.6 Arial;' +
      'background:rgba(0,0,0,0.45);padding:8px 12px;border-radius:8px;z-index:1000;' +
      'max-width:46vw;pointer-events:none;';
    // Touch devices have no keyboard — steer via the command sliders instead of WASD, and the
    // mouse verbs become touch gestures (DragStateManager/OrbitControls are pointer-event based,
    // so the drag/orbit/zoom interactions themselves already work under touch).
    const coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    const lines = [coarse
      ? '👆 로봇 끌기 = 밀기 · 한 손가락 = 회전 · 두 손가락 = 줌'
      : '🖱 로봇 드래그 = 밀기 · 빈곳 드래그 = 회전 · 휠 = 줌'];
    if (this.policy) {
      lines.unshift(coarse ? '🕹 슬라이더로 조종 (vx/vy/vyaw)' : '⌨ WASD 이동 · Q/E 회전 · Space 일시정지');
    }
    if (this.teleopCfg) {
      lines.push('🤏 Teleop 켠 뒤 ' + (coarse ? '끌기' : '드래그') + ' = 팔 끝 IK 조종');
    }
    hint.innerHTML = lines.join('<br>');
    this.container.appendChild(hint);
  }

  // (C) Mouse EE teleop for fixed-base arms. Drag a body and damped-LS IK chases the mouse
  // point with the gripper. The Jacobian is built by finite differences (perturb each actuated
  // joint, mj_forward, read the EE body's xpos delta) — binding-agnostic, reuses only the
  // qpos/xpos + mj_forward calls already in use (mj_jacBody's output args are awkward in this
  // wasm build). Honest about reach: SO-100's 5-DOF can't hold arbitrary poses (M6/ADR 0004),
  // so the EE simply tracks as close as the damped solution allows — it won't snap to the mouse.
  initTeleop() {
    const m = this.model, mj = this.mujoco;
    const eeId = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY.value, this.teleopCfg.ee_body);
    const joints = [];
    const JOINT = mj.mjtTrn.mjTRN_JOINT.value;
    for (let i = 0; i < m.nu; i++) {
      // Only joint-driven actuators (skip e.g. Panda's tendon gripper — its trnid is a tendon id).
      if (m.actuator_trntype[i] !== JOINT) { continue; }
      const jid = m.actuator_trnid[2 * i];
      if (jid < 0) { continue; }
      joints.push({
        q: m.jnt_qposadr[jid], d: m.jnt_dofadr[jid], u: i,
        lo: m.jnt_range[2 * jid], hi: m.jnt_range[2 * jid + 1],
        clo: m.actuator_ctrlrange[2 * i], chi: m.actuator_ctrlrange[2 * i + 1],
      });
    }
    this.tele = { eeId, joints, target: new THREE.Vector3(), active: false, enabled: false };
    this.gui.add(this.tele, 'enabled').name('🤏 Teleop arm (drag gripper)').onChange((v) => {
      if (v) {   // hand control to IK: freeze replay/physics, IK drives qpos in render()
        this.params.replay = false; this.params.paused = false;
        if (this.replayToggle) { this.replayToggle.updateDisplay(); }
      }
    });
  }

  // Teleop step (called from render when tele.enabled): pull the IK target from the live drag
  // point while a body is grabbed and run one IK step toward it; otherwise just hold the pose.
  // The final mj_forward (here or inside solveIK) refreshes xpos for the body-transform update.
  stepTeleop() {
    const drag = this.dragStateManager;
    if (drag.physicsObject && drag.physicsObject.bodyID) {
      drag.update();
      const w = toMujocoPos(drag.currentWorld.clone());
      this.tele.target.set(w.x, w.y, w.z);
      this.solveIK();
    } else {
      this.mujoco.mj_forward(this.model, this.data);
    }
  }

  // One damped-least-squares IK step toward this.tele.target (MuJoCo coords). Mutates qpos of the
  // actuated arm joints + mirrors into ctrl (position actuators). Velocities zeroed for stability.
  solveIK() {
    const m = this.model, d = this.data, mj = this.mujoco, T = this.tele, J = T.joints, n = J.length;
    const eb = 3 * T.eeId, eps = 1e-4, STEP = 0.05, l2 = 0.04 * 0.04;
    mj.mj_forward(m, d);
    const p0 = [d.xpos[eb], d.xpos[eb + 1], d.xpos[eb + 2]];
    let e = [T.target.x - p0[0], T.target.y - p0[1], T.target.z - p0[2]];
    const emag = Math.hypot(e[0], e[1], e[2]);
    if (emag > STEP) { const s = STEP / emag; e = e.map((v) => v * s); }   // clamp EE step/frame
    // finite-difference position Jacobian (3 x n)
    const Jac = [new Array(n), new Array(n), new Array(n)];
    for (let j = 0; j < n; j++) {
      const q = J[j].q, save = d.qpos[q];
      d.qpos[q] = save + eps; mj.mj_forward(m, d);
      Jac[0][j] = (d.xpos[eb] - p0[0]) / eps;
      Jac[1][j] = (d.xpos[eb + 1] - p0[1]) / eps;
      Jac[2][j] = (d.xpos[eb + 2] - p0[2]) / eps;
      d.qpos[q] = save;
    }
    mj.mj_forward(m, d);
    // A = J Jt + l2 I  (3x3);  y = A^-1 e;  dq = Jt y
    const A = [[l2, 0, 0], [0, l2, 0], [0, 0, l2]];
    for (let a = 0; a < 3; a++) { for (let b = 0; b < 3; b++) { let s = 0; for (let j = 0; j < n; j++) { s += Jac[a][j] * Jac[b][j]; } A[a][b] += s; } }
    const y = this.solve3(A, e);
    for (let j = 0; j < n; j++) {
      let s = 0; for (let a = 0; a < 3; a++) { s += Jac[a][j] * y[a]; }
      let nq = d.qpos[J[j].q] + s;
      if (J[j].hi > J[j].lo) { nq = Math.min(J[j].hi, Math.max(J[j].lo, nq)); }   // joint limit
      d.qpos[J[j].q] = nq;
      let cu = nq;
      if (J[j].chi > J[j].clo) { cu = Math.min(J[j].chi, Math.max(J[j].clo, nq)); }
      d.ctrl[J[j].u] = cu;
      d.qvel[J[j].d] = 0;
    }
  }

  // Solve 3x3 A x = b by Cramer's rule (A is small + well-conditioned via the l2 damping).
  solve3(A, b) {
    const det = (a) =>
      a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) -
      a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) +
      a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    const D = det(A);
    if (Math.abs(D) < 1e-12) { return [0, 0, 0]; }
    const col = (a, c, v) => a.map((row, i) => row.map((x, j) => (j === c ? v[i] : x)));
    return [det(col(A, 0, b)) / D, det(col(A, 1, b)) / D, det(col(A, 2, b)) / D];
  }

  // (A) Live learned-policy closed loop. ONNX policy + obs construction are byte-parity with
  // training (experiment 04 obs_spec) — validated headlessly (tmp_test_go1_loop.mjs: t=0 obs
  // exact, walks in wasm). onnxruntime-web inference is async, so it runs in a self-paced
  // ~50Hz control loop decoupled from the render loop (which just displays sim state).
  async initPolicy() {
    const ort = await import('https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/ort.min.mjs');
    ort.env.wasm.wasmPaths = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.20.1/dist/';
    this.ort = ort;
    const p = this.policy, ix = p.indices;
    const sceneDir = this.params.scene.split('/')[0];   // onnx lives next to its bundled scene
    this.pol = {
      onnx: './assets/scenes/' + sceneDir + '/' + p.onnx,
      obs_dim: p.obs_dim, act_dim: p.act_dim, action_scale: p.action_scale,
      n_substeps: p.n_substeps, command: p.command,
      gy: ix.gyro_adr, lv: ix.local_linvel_adr, imu: ix.imu_site_id,
      qj: p.qpos_joint_start, vj: p.qvel_joint_start, dp: ix.default_pose,
      lastAct: new Float32Array(p.act_dim),
      obs_layout: p.obs_layout || null,
      obsHistory: p.obs_history ? new Float32Array(p.obs_dim) : null,
      currentObsDim: p.obs_history?.current_dim || 0,
      commandTransform: p.command_transform || [1, 1, 1],
      commandScale: p.command_scale || [1, 1, 1],
      // gait phase clock (humanoid joystick policies, e.g. G1): a 2-vec advanced each control
      // step by phase_dt; obs uses concat([cos(phase),sin(phase)]). null for policies w/o gait.
      phase: p.gait ? Float64Array.from(p.gait.phase_init) : null,
      phaseDt: p.gait ? 2 * Math.PI * p.ctrl_dt * p.gait.gait_freq : 0,
      cmdRange: p.command_range || null,
      // Spot extras (null/no-op for go1/G1): gravity = upvector sensor, feet = 4 framepos sensor
      // adrs, lowers/uppers = ctrl clip, qposErrHistory = stateful 3-step joint-error buffer.
      grav: ix.upvector_adr ?? null,
      feet: ix.feet_adrs || null,
      lowers: ix.lowers || null,
      uppers: ix.uppers || null,
      qposErrHistory: p.history_len ? new Float32Array(p.history_len * 12) : null,
      motorTargets: new Float32Array(p.act_dim),
    };
    // seed home keyframe (key 0)
    for (let i = 0; i < this.model.nq; i++) { this.data.qpos[i] = this.model.key_qpos[i]; }
    for (let i = 0; i < this.data.qvel.length; i++) { this.data.qvel[i] = 0; }
    for (let i = 0; i < this.model.nu; i++) { this.data.ctrl[i] = this.pol.dp[i]; }
    this.mujoco.mj_forward(this.model, this.data);

    this.session = await this.ort.InferenceSession.create(this.pol.onnx);
    this.params.policyRunning = true;
    this.runPolicyLoop();
  }

  // Interactive joystick: bind the velocity command [vx, vy, vyaw] to GUI sliders. This is a
  // joystick-conditioned policy (command is part of the obs), so dragging a slider steers the
  // live robot — buildPolicyObs reads this.pol.command in place every control step.
  addCommandGUI() {
    const c = this.pol.command;
    const r = this.pol.cmdRange || { vx: [-1.0, 1.5], vy: [-0.8, 0.8], vyaw: [-1.5, 1.5] };
    const f = this.gui.addFolder('Command (drag or WASD/QE to steer)');
    this.cmdControllers = [
      f.add(c, '0', r.vx[0], r.vx[1], 0.05).name('vx  forward'),
      f.add(c, '1', r.vy[0], r.vy[1], 0.05).name('vy  strafe'),
      f.add(c, '2', r.vyaw[0], r.vyaw[1], 0.05).name('vyaw  turn'),
    ];
    f.open();
    this.bindCommandKeys(r);
  }

  // Keyboard steering: hold W/S → +/- vx, A/D → +/- vy (left/right), Q/E → +/- vyaw (turn
  // left/right). A held key sets that command axis to the range edge; releasing it returns the
  // axis to 0. Keys are tracked in a set so axes combine (W+A = forward-left). The command is
  // part of the policy obs (joystick-conditioned), so this drives the live robot exactly like
  // the sliders — sliders are refreshed via updateDisplay so the GUI mirrors the keys.
  bindCommandKeys(r) {
    const c = this.pol.command;
    const held = new Set();
    const keys = new Set(['w', 'a', 's', 'd', 'q', 'e']);
    const apply = () => {
      c[0] = held.has('w') ? r.vx[1]   : held.has('s') ? r.vx[0]   : 0;
      c[1] = held.has('a') ? r.vy[1]   : held.has('d') ? r.vy[0]   : 0;
      c[2] = held.has('q') ? r.vyaw[1] : held.has('e') ? r.vyaw[0] : 0;
      for (const ctl of this.cmdControllers) { ctl.updateDisplay(); }
    };
    // Ignore keystrokes while a GUI text field has focus, so typing a value isn't hijacked.
    const typing = (e) => e.target && /^(INPUT|TEXTAREA)$/.test(e.target.tagName);
    window.addEventListener('keydown', (e) => {
      const k = e.key.toLowerCase();
      if (!keys.has(k) || typing(e)) { return; }
      held.add(k); apply(); e.preventDefault();
    });
    window.addEventListener('keyup', (e) => {
      const k = e.key.toLowerCase();
      if (!keys.has(k)) { return; }
      held.delete(k); apply(); e.preventDefault();
    });
  }

  // Build the policy obs by walking the experiment's obs_layout (named slots), so a new
  // embodiment with a different obs (order / joint count / gait clock) needs zero JS changes —
  // it's the same single-source-of-truth as obs_spec.json. Read sensordata AS-IS (1-substep
  // stale, same as training) — do NOT mj_forward first. gravity = -(site_xmat third row) =
  // site_xmat.T @ [0,0,-1]. Slot dims come from p.act_dim (joints) so go1(12) and G1(29) both work.
  //   go1 obs(48): [local_linvel, gyro, gravity, joints, joint_vel, last_act, command]
  //   G1  obs(103):[local_linvel, gyro, gravity, command, joints, joint_vel, last_act, phase_cos_sin]
  buildPolicyObs() {
    const d = this.data, p = this.pol, o = new Float32Array(p.obs_dim), nu = p.act_dim;
    if (p.obsHistory) {
      const cur = new Float32Array(p.currentObsDim);
      let j = 0;
      cur[j++] = d.sensordata[p.gy + 2] * 0.25;       // Barkour _get_localrpyrate(data)[-1] * 0.25
      for (let i = 0; i < 3; i++) { cur[j++] = d.sensordata[p.grav + i]; }
      for (let i = 0; i < 3; i++) {
        cur[j++] = p.command[i] * p.commandTransform[i] * p.commandScale[i];
      }
      for (let i = 0; i < nu; i++) { cur[j++] = d.qpos[p.qj + i] - p.dp[i]; }
      for (let i = 0; i < nu; i++) { cur[j++] = p.lastAct[i]; }
      p.obsHistory.copyWithin(p.currentObsDim, 0, p.obsHistory.length - p.currentObsDim);
      p.obsHistory.set(cur, 0);
      return p.obsHistory;
    }
    const x = p.imu * 9;
    let k = 0;
    for (const [name] of p.obs_layout) {
      switch (name) {
        case 'local_linvel': for (let i = 0; i < 3; i++) { o[k++] = d.sensordata[p.lv + i]; } break;
        case 'gyro':         for (let i = 0; i < 3; i++) { o[k++] = d.sensordata[p.gy + i]; } break;
        case 'gravity':      o[k++] = -d.site_xmat[x + 6]; o[k++] = -d.site_xmat[x + 7]; o[k++] = -d.site_xmat[x + 8]; break;
        // Spot: gravity_projected = upvector sensor (3); feet_pos = 4 framepos sensors (FL,FR,HL,HR
        // order, trunk-relative, 12); qpos_error_history = stateful 3-step buffer (36).
        case 'gravity_projected': for (let i = 0; i < 3; i++) { o[k++] = d.sensordata[p.grav + i]; } break;
        case 'feet_pos':     for (const a of p.feet) { for (let i = 0; i < 3; i++) { o[k++] = d.sensordata[a + i]; } } break;
        case 'qpos_error_history': { const h = p.qposErrHistory; for (let i = 0; i < h.length; i++) { o[k++] = h[i]; } } break;
        case 'command':      for (let i = 0; i < 3; i++) { o[k++] = p.command[i]; } break;
        case 'joint_angles_minus_default': for (let i = 0; i < nu; i++) { o[k++] = d.qpos[p.qj + i] - p.dp[i]; } break;
        case 'joint_vel':    for (let i = 0; i < nu; i++) { o[k++] = d.qvel[p.vj + i]; } break;
        case 'last_act':     for (let i = 0; i < nu; i++) { o[k++] = p.lastAct[i]; } break;
        case 'phase_cos_sin': o[k++] = Math.cos(p.phase[0]); o[k++] = Math.cos(p.phase[1]);
                              o[k++] = Math.sin(p.phase[0]); o[k++] = Math.sin(p.phase[1]); break;
      }
    }
    return o;
  }

  // Advance the gait phase clock one control step (no-op if the policy has no gait):
  // phase += phase_dt, wrapped to [-pi, pi). Must be called once per control step, AFTER mj_step,
  // mirroring the training env's step() so the web phase sequence matches golden byte-for-byte.
  advancePhase() {
    const p = this.pol;
    if (!p.phase) return;
    const TWO = 2 * Math.PI;
    for (let i = 0; i < p.phase.length; i++) {
      p.phase[i] = (((p.phase[i] + p.phaseDt + Math.PI) % TWO) + TWO) % TWO - Math.PI;
    }
  }

  // Roll the qpos-error history one control step (no-op if the policy has no history, e.g. go1/G1):
  // prepend (joint_angles - last motor_targets), drop the oldest. Called BEFORE buildPolicyObs each
  // step, mirroring the env's _get_obs ordering so the web buffer matches golden byte-for-byte.
  advanceHistory() {
    const p = this.pol;
    if (!p.qposErrHistory) return;
    const h = p.qposErrHistory, nu = p.act_dim, qj = p.qj;
    h.copyWithin(nu, 0, h.length - nu);   // shift older errors back by one slot (= np.roll(h, 12))
    for (let i = 0; i < nu; i++) { h[i] = this.data.qpos[qj + i] - p.motorTargets[i]; }
  }

  // One control step's policy compute: update history, build obs, run onnx, set ctrl. Shared by the
  // real-time loop and the QA stepper so both stay byte-identical. motor_targets = clip(default +
  // act*scale, [lowers, uppers]) — the clip matters for Spot's history (no-op clip for go1/G1).
  async computeAndApplyAction() {
    const p = this.pol, A = p.action_scale;
    this.advanceHistory();
    const obs = this.buildPolicyObs();
    const out = await this.session.run({ obs: new this.ort.Tensor('float32', obs, [1, p.obs_dim]) });
    const act = out[Object.keys(out)[0]].data;
    for (let i = 0; i < p.act_dim; i++) {
      p.lastAct[i] = act[i];
      let mt = p.dp[i] + act[i] * A;
      if (p.lowers) { mt = Math.min(p.uppers[i], Math.max(p.lowers[i], mt)); }
      p.motorTargets[i] = mt;
      this.data.ctrl[i] = mt;
    }
  }

  async runPolicyLoop() {
    const p = this.pol, nsub = p.n_substeps;
    while (this.params.policyRunning) {
      const t0 = performance.now();
      if (!this.params.paused) {
        await this.computeAndApplyAction();
        // optional drag force — poke the walking robot
        for (let i = 0; i < this.data.qfrc_applied.length; i++) { this.data.qfrc_applied[i] = 0.0; }
        const dragged = this.dragStateManager.physicsObject;
        if (dragged && dragged.bodyID) {
          this.dragStateManager.update();
          const f = toMujocoPos(this.dragStateManager.currentWorld.clone().sub(this.dragStateManager.worldHit).multiplyScalar(this.model.body_mass[dragged.bodyID] * 250));
          const pt = toMujocoPos(this.dragStateManager.worldHit.clone());
          this.mujoco.mj_applyFT(this.model, this.data, [f.x, f.y, f.z], [0, 0, 0], [pt.x, pt.y, pt.z], dragged.bodyID, this.data.qfrc_applied);
        }
        for (let s = 0; s < nsub; s++) { this.mujoco.mj_step(this.model, this.data); }
        this.advancePhase();
      }
      const dt = performance.now() - t0;
      await new Promise((r) => setTimeout(r, Math.max(0, 20 - dt)));   // ~50Hz real-time
    }
  }

  // QA hook (window.demo.qaStep): deterministically drive the closed loop n control steps
  // then render one frame. Bypasses runPolicyLoop's setTimeout pacing, which headless chromium
  // throttles to ~1Hz — so automated screenshots capture real walking. Sets paused=true so the
  // background loop stops stepping (no double-step race); qaStep does all the stepping itself.
  // Returns diagnostics so the harness can assert walk progress / fall / NaN without eyeballing.
  async qaStep(n = 50) {
    if (!this.pol) return { error: 'no policy in this experiment' };
    const p = this.pol, nsub = p.n_substeps;
    this.params.paused = true;
    for (let step = 0; step < n; step++) {
      await this.computeAndApplyAction();
      for (let s = 0; s < nsub; s++) { this.mujoco.mj_step(this.model, this.data); }
      this.advancePhase();
    }
    this.render(0);
    let nan = false;
    for (let i = 0; i < this.model.nq; i++) { if (!Number.isFinite(this.data.qpos[i])) { nan = true; break; } }
    const h = this.data.qpos[2];
    const qw = this.data.qpos[3], qx = this.data.qpos[4], qy = this.data.qpos[5], qz = this.data.qpos[6];
    const yaw = Math.atan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz));
    return {
      steps: n,
      x: this.data.qpos[0],
      y: this.data.qpos[1],
      yaw,
      height: h,
      fell: h < 0.2,
      nan,
      command: Array.from(p.command),
    };
  }

  // QA hook for replay (non-policy) experiments: seek to a trajectory frame (frac in [0,1])
  // and render it. Freezes auto-replay (replay=false) + paused so the seeked pose isn't
  // overwritten by the wall-clock playhead. Lets the harness screenshot any frame on demand.
  qaSeek(frac) {
    if (!this.replayQpos) return { error: 'no replay' };
    this.params.replay = false; this.params.paused = true;
    const f = Math.max(0, Math.min(this.replayN - 1, Math.round(frac * (this.replayN - 1))));
    const q = this.replayQpos[f];
    for (let i = 0; i < this.model.nq; i++) { this.data.qpos[i] = q[i]; }
    this.mujoco.mj_forward(this.model, this.data);
    this.render(0);
    return { frame: f, nframes: this.replayN, nq: this.model.nq };
  }

  // QA hook for EE teleop: enable teleop, set the IK target to (start EE + delta) and run n IK
  // steps — no human drag — then report the residual so the harness can assert the arm tracks.
  qaTeleop(delta, n = 80) {
    if (!this.tele) { return { error: 'no teleop in this experiment' }; }
    this.tele.enabled = true; this.params.replay = false; this.params.paused = false;
    this.mujoco.mj_forward(this.model, this.data);
    const eb = 3 * this.tele.eeId;
    const start = [this.data.xpos[eb], this.data.xpos[eb + 1], this.data.xpos[eb + 2]];
    const target = [start[0] + delta[0], start[1] + delta[1], start[2] + delta[2]];
    this.tele.target.set(target[0], target[1], target[2]);
    for (let i = 0; i < n; i++) { this.solveIK(); }
    this.render(0);
    const ee = [this.data.xpos[eb], this.data.xpos[eb + 1], this.data.xpos[eb + 2]];
    const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
    let nan = false;
    for (let i = 0; i < this.model.nq; i++) { if (!Number.isFinite(this.data.qpos[i])) { nan = true; break; } }
    return { start, target, ee, residual: dist(ee, target), startResidual: dist(start, target), nan };
  }

  // Seed the scene from a recorded trajectory frame (qpos + arm ctrl + zero velocity).
  seedFrame(frame) {
    const q = this.replayQpos[frame];
    for (let i = 0; i < this.model.nq; i++) { this.data.qpos[i] = q[i]; }
    for (let i = 0; i < this.data.qvel.length; i++) { this.data.qvel[i] = 0; }
    for (let i = 0; i < this.model.nu; i++) { this.data.ctrl[i] = q[i]; }  // arm home = qpos[0..5]
    this.mujoco.mj_forward(this.model, this.data);
  }

  onWindowResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize( window.innerWidth, window.innerHeight );
  }

  render(timeMS) {
    // Follow the walking robot: the free-joint root pose is qpos[0..2] (MuJoCo Z-up ->
    // three.js Y-up swizzle: x, z, -y). Shift target + camera by the same delta so the
    // camera rigidly tracks the robot while the user can still orbit around it.
    if (this.policy && this.data) {
      this.tmpVec.set(this.data.qpos[0], this.data.qpos[2], -this.data.qpos[1]);
      const delta = this.tmpVec.sub(this.controls.target);
      this.controls.target.add(delta);
      this.camera.position.add(delta);
    }
    this.controls.update();

    if (this.tele && this.tele.enabled) {
      // (C) EE teleop: IK drives the arm toward the drag point; replay/physics suspended.
      this.stepTeleop();
    } else if (this.params["replay"] && this.replayQpos) {
      // Grab-to-take-over: if the user starts dragging a body mid-replay, auto-pause the
      // rollout *in place* and hand off to physics. Hold the current pose (ctrl = current
      // qpos) so the arm doesn't snap to home, and don't reset (unlike the manual toggle).
      const grabbed = this.dragStateManager.physicsObject;
      if (grabbed && grabbed.bodyID) {
        this.params.replay = false;
        this.replayToggle.updateDisplay();
        for (let i = 0; i < this.model.nu; i++) { this.data.ctrl[i] = this.data.qpos[i]; }
      } else {
        // Kinematic playback: advance the playhead in real time and loop. The trajectory
        // has built-in holds at home (start/end), so a plain wrap gives the pause-at-ends.
        if (this.replayStartMS === null) { this.replayStartMS = timeMS; }
        let frame = Math.floor(((timeMS - this.replayStartMS) / 1000.0) * this.replayFps) % this.replayN;
        if (!(frame >= 0)) { frame = 0; }
        const q = this.replayQpos[frame];
        for (let i = 0; i < q.length; i++) { this.data.qpos[i] = q[i]; }
        this.mujoco.mj_forward(this.model, this.data);
      }
    } else if (!this.params["replay"] && !this.params["paused"]) {
      let timestep = this.model.opt.timestep;
      if (timeMS - this.mujoco_time > 35.0) { this.mujoco_time = timeMS; }
      while (this.mujoco_time < timeMS) {

        // Jitter the control state with gaussian random noise
        if (this.params["ctrlnoisestd"] > 0.0) {
          let rate  = Math.exp(-timestep / Math.max(1e-10, this.params["ctrlnoiserate"]));
          let scale = this.params["ctrlnoisestd"] * Math.sqrt(1 - rate * rate);
          let currentCtrl = this.data.ctrl;
          for (let i = 0; i < currentCtrl.length; i++) {
            currentCtrl[i] = rate * currentCtrl[i] + scale * standardNormal();
            this.params["Actuator " + i] = currentCtrl[i];
          }
        }

        // Clear old perturbations, apply new ones.
        for (let i = 0; i < this.data.qfrc_applied.length; i++) { this.data.qfrc_applied[i] = 0.0; }
        let dragged = this.dragStateManager.physicsObject;
        if (dragged && dragged.bodyID) {
          for (let b = 0; b < this.model.nbody; b++) {
            if (this.bodies[b]) {
              getPosition  (this.data.xpos , b, this.bodies[b].position);
              getQuaternion(this.data.xquat, b, this.bodies[b].quaternion);
              this.bodies[b].updateWorldMatrix();
            }
          }
          let bodyID = dragged.bodyID;
          this.dragStateManager.update(); // Update the world-space force origin
          let force = toMujocoPos(this.dragStateManager.currentWorld.clone().sub(this.dragStateManager.worldHit).multiplyScalar(this.model.body_mass[bodyID] * 250));
          let point = toMujocoPos(this.dragStateManager.worldHit.clone());
          mujoco.mj_applyFT(this.model, this.data, [force.x, force.y, force.z], [0, 0, 0], [point.x, point.y, point.z], bodyID, this.data.qfrc_applied);

          // TODO: Apply pose perturbations (mocap bodies only).
        }

        mujoco.mj_step(this.model, this.data);

        this.mujoco_time += timestep * 1000.0;
      }

    } else if (this.params["paused"]) {
      this.dragStateManager.update(); // Update the world-space force origin
      let dragged = this.dragStateManager.physicsObject;
      if (dragged && dragged.bodyID) {
        let b = dragged.bodyID;
        getPosition  (this.data.xpos , b, this.tmpVec , false); // Get raw coordinate from MuJoCo
        getQuaternion(this.data.xquat, b, this.tmpQuat, false); // Get raw coordinate from MuJoCo

        let offset = toMujocoPos(this.dragStateManager.currentWorld.clone()
          .sub(this.dragStateManager.worldHit).multiplyScalar(0.3));
        if (this.model.body_mocapid[b] >= 0) {
          // Set the root body's mocap position...
          console.log("Trying to move mocap body", b);
          let addr = this.model.body_mocapid[b] * 3;
          let pos  = this.data.mocap_pos;
          pos[addr+0] += offset.x;
          pos[addr+1] += offset.y;
          pos[addr+2] += offset.z;
        } else {
          // Set the root body's position directly...
          let root = this.model.body_rootid[b];
          let addr = this.model.jnt_qposadr[this.model.body_jntadr[root]];
          let pos  = this.data.qpos;
          pos[addr+0] += offset.x;
          pos[addr+1] += offset.y;
          pos[addr+2] += offset.z;
        }
      }

      mujoco.mj_forward(this.model, this.data);
    }

    // Update body transforms.
    for (let b = 0; b < this.model.nbody; b++) {
      if (this.bodies[b]) {
        getPosition  (this.data.xpos , b, this.bodies[b].position);
        getQuaternion(this.data.xquat, b, this.bodies[b].quaternion);
        this.bodies[b].updateWorldMatrix();
      }
    }

    // Update light transforms.
    for (let l = 0; l < this.model.nlight; l++) {
      if (this.lights[l]) {
        getPosition(this.data.light_xpos, l, this.lights[l].position);
        getPosition(this.data.light_xdir, l, this.tmpVec);
        this.lights[l].lookAt(this.tmpVec.add(this.lights[l].position));
      }
    }

    // Draw Tendons and Flex verts
    drawTendonsAndFlex(this.mujocoRoot, this.model, this.data);

    // Render!
    this.renderer.render( this.scene, this.camera );
  }
}

let demo = new MuJoCoDemo();
await demo.init();
window.demo = demo;   // expose for QA/debugging (read demo.data.qpos[0] for walk progress)
