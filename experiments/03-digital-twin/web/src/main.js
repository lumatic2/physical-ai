
import * as THREE           from 'three';
import { GUI              } from 'three/addons/libs/lil-gui.module.min.js';
import { OrbitControls    } from 'three/addons/controls/OrbitControls.js';
import { DragStateManager } from './utils/DragStateManager.js';
import { setupGUI, downloadExampleScenesFolder, loadSceneFromURL, drawTendonsAndFlex, getPosition, getQuaternion, toMujocoPos, standardNormal } from './mujocoUtils.js';
import { DEFAULT_ENVIRONMENT_PRESET, ENVIRONMENT_PRESETS, ENVIRONMENT_SCENARIOS, EPISODE_COMPARISON_PROFILES, EPISODE_RANDOMIZATION_PROFILES, GROUNDING_MODES, getEnvironmentScenario, inferEnvironmentPresetFromExperiment, inferEnvironmentScenarioFromExperiment, inferGroundingModeFromExperiment, normalizeEnvironmentPresetId, normalizeEnvironmentScenarioId, normalizeGroundingMode, summarizeEnvironmentPreset, summarizeEnvironmentScenario, summarizeEpisodeComparisonProfile, summarizeEpisodeRandomizationProfile } from './environmentPresets.js';
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
    this.showDebugControls = new URLSearchParams(window.location.search).get("debug") === "1";

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

    this.labVisualLayer = new THREE.Group();
    this.labVisualLayer.name = "Lab Visual Layer";
    this.scene.add(this.labVisualLayer);
    this.appliedEnvironmentVisual = null;
    this.labAssetLayerStatus = {
      path: "assets/lab/lab_shell.gltf",
      loaded: false,
      loading: false,
      objectCount: 0,
      error: null,
    };
    this.labAssetLoadToken = 0;
    this.commandHeld = new Set();
    this.commandRange = null;
    this.lastCommandInputSource = 'initial';

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
    // desktop smoke/render/record read. The public default is a stable standing humanoid;
    // policy locomotion starts when the visitor selects a walking action.
    const registry = await (await fetch("./experiments.json")).json();
    const params = new URLSearchParams(location.search);
    const expName = params.get("exp") || registry.default;
    this.registry = registry;
    this.environmentPresetExplicit = params.has("env");
    this.environmentScenarioExplicit = params.has("scenario");
    this.requestedEnvironmentScenarioId = params.get("scenario") || null;
    this.episodeRandomizationProfileId = params.get("episodeProfile") || "obstacle-command-noise-v1";
    this.episodeComparisonProfileId = params.get("comparisonProfile") || "obstacle-command-noise-comparison-v1";
    const inferredScenarioId = normalizeEnvironmentScenarioId(
      this.requestedEnvironmentScenarioId || inferEnvironmentScenarioFromExperiment(registry.experiments?.[expName] || {}),
    );
    const inferredScenario = getEnvironmentScenario(inferredScenarioId);
    this.environmentPresetId = normalizeEnvironmentPresetId(
      params.get("env") || inferredScenario.preset || inferEnvironmentPresetFromExperiment(registry.experiments?.[expName] || {}),
    );
    this.environmentScenarioId = normalizeEnvironmentScenarioId(inferredScenarioId, this.environmentPresetId);
    this.requestedGroundingMode = params.get("grounding") || null;
    this.streamUrl = params.get("stream");
    await this.switchExperiment(expName, { updateUrl: false, initial: true });
  }

  cleanupExperimentRuntime() {
    this.isSwitchingExperiment = true;
    this.params.policyRunning = false;
    this.policyRunId = (this.policyRunId || 0) + 1;
    if (this.streamSocket) {
      try { this.streamSocket.close(); } catch {}
      this.streamSocket = null;
    }
    if (this.gui) {
      try { this.gui.destroy(); } catch {}
      this.gui = null;
    }
    if (this.controlHintEl) {
      this.controlHintEl.remove();
      this.controlHintEl = null;
    }
    if (this.unbindCommandKeys) {
      this.unbindCommandKeys();
      this.unbindCommandKeys = null;
    }
    const root = this.scene.getObjectByName("MuJoCo Root");
    if (root) {
      root.traverse((object) => {
        object.geometry?.dispose?.();
        if (Array.isArray(object.material)) {
          object.material.forEach((material) => material.dispose?.());
        } else {
          object.material?.dispose?.();
        }
      });
      this.scene.remove(root);
    }
    this.policy = null;
    this.pol = null;
    this.commandHeld = new Set();
    this.commandRange = null;
    this.lastCommandInputSource = 'initial';
    this.session = null;
    this.replayQpos = null;
    this.replayN = null;
    this.telemetry = null;
    this.compare = null;
    this.teleopCfg = null;
    this.tele = null;
    this.streamFrame = null;
    this.streamStats = null;
    this.cmdControllers = null;
    this.replayToggle = null;
  }

  async switchExperiment(expName, options = {}) {
    const registry = this.registry;
    if (!registry?.experiments) throw new Error("experiment registry not loaded");
    const nextName = registry.experiments[expName] ? expName : registry.default;
    const exp = registry.experiments[nextName];
    const previousName = this.expName;
    const switchingScene = !options.initial;

    if (switchingScene) {
      this.cleanupExperimentRuntime();
      window.dispatchEvent(new CustomEvent('robotics-lab-experiment-change', {
        detail: { phase: 'loading', experiment: nextName, previous: previousName },
      }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    }

    if (options.updateUrl !== false) {
      const next = new URL(window.location.href);
      next.searchParams.set("exp", nextName);
      window.history.pushState({ exp: nextName }, "", next.toString());
    }

    this.expName = nextName;
    this.exp = exp;
    this.currentMeta = null;
    if (!this.environmentScenarioExplicit) {
      this.environmentScenarioId = normalizeEnvironmentScenarioId(inferEnvironmentScenarioFromExperiment(exp));
    }
    const scenario = getEnvironmentScenario(this.environmentScenarioId, this.environmentPresetId);
    if (this.environmentScenarioExplicit || !this.environmentPresetExplicit) {
      this.environmentPresetId = normalizeEnvironmentPresetId(scenario.preset || inferEnvironmentPresetFromExperiment(exp));
    }
    this.groundingMode = normalizeGroundingMode(
      this.requestedGroundingMode || inferGroundingModeFromExperiment(exp),
      ENVIRONMENT_PRESETS[this.environmentPresetId].grounding.allowedModes,
      ENVIRONMENT_PRESETS[this.environmentPresetId].grounding.defaultMode,
    );
    this.params = {
      scene: exp.scene,
      paused: false,
      help: false,
      ctrlnoiserate: 0.0,
      ctrlnoisestd: 0.0,
      keyframeNumber: 0,
      replay: true,
      policyRunning: false,
    };

    [this.model, this.data, this.bodies, this.lights] =
      await loadSceneFromURL(mujoco, exp.scene, this);

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
      if (this.showDebugControls) {
        this.gui = new GUI();
        setupGUI(this);
        this.addCommandGUI();
      } else {
        this.bindCommandKeys(this.pol.cmdRange || { vx: [-1.0, 1.5], vy: [-0.8, 0.8], vyaw: [-1.5, 1.5] });
      }
    } else {
      // (B) replay: NOTE the 'home' keyframe may pad free-joints to the origin, so we
      // seed from trajectory frame 0.
      const traj = await (await fetch("./" + exp.trajectory)).json();
      this.replayFps = traj.fps;
      this.replayQpos = traj.qpos;            // [frame][nq]
      this.replayN = traj.qpos.length;
      this.telemetry = null;
      if (exp.telemetry_sidecar) {
        const telemetry = await (await fetch("./" + exp.telemetry_sidecar)).json();
        const frames = Array.isArray(telemetry.frames) ? telemetry.frames : [];
        if (frames.length === this.replayN) {
          this.telemetry = telemetry;
        } else {
          console.warn(`telemetry_sidecar frame mismatch: ${frames.length} vs ${this.replayN}`);
        }
      }
      this.compare = null;
      if (exp.compare_trajectory) {
        const compareTraj = await (await fetch("./" + exp.compare_trajectory)).json();
        const compareQpos = Array.isArray(compareTraj.qpos) ? compareTraj.qpos : [];
        if (compareQpos.length > 0 && compareQpos[0].length === this.model.nq) {
          this.compare = {
            label: exp.compare_label || 'Reference',
            rolloutLabel: exp.rollout_label || 'Rollout',
            qpos: compareQpos,
            fps: compareTraj.fps || this.replayFps,
            source: exp.compare_trajectory,
          };
        } else {
          console.warn(`compare_trajectory invalid for nq=${this.model.nq}: ${exp.compare_trajectory}`);
        }
      }
      this.replayStartMS = null;
      this.seedFrame(0);
      this.streamFrame = null;
      this.streamStats = {
        enabled: false,
        connected: false,
        received: 0,
        errors: 0,
        droppedOrOutOfOrder: 0,
        repeatedTicks: 0,
        lastTick: null,
        firstReceiveMS: null,
        lastReceiveMS: null,
        minHeight: null,
        maxHeight: null,
      };

      if (this.showDebugControls) {
        this.gui = new GUI();
        setupGUI(this);
        // Replay toggle — default on. Off hands control back to physics + drag.
        this.replayToggle = this.gui.add(this.params, 'replay').name('▶ Replay (grab to take over)').onChange((v) => {
          this.replayStartMS = null;
          if (!v) { this.seedFrame(0); }
        });
      }
      // (C) EE teleop for fixed-base arms (experiments.json `teleop: true`).
      this.teleopCfg = exp.teleop ? { ee_body: exp.ee_body } : null;
      if (this.teleopCfg && this.showDebugControls) { this.initTeleop(); }
      const streamUrl = new URLSearchParams(location.search).get("stream");
      if (this.streamUrl || streamUrl) { this.initTelemetryStream(this.streamUrl || streamUrl); }
    }

    if (this.showDebugControls) {
      this.addControlHints();
    }
    if (!document.getElementById('ui-root')) {
      this.addProjectOverlay();
    }
    this.applyEnvironmentVisuals();
    this.dispatchEnvironmentChange();
    this.isSwitchingExperiment = false;
    window.dispatchEvent(new CustomEvent('robotics-lab-experiment-change', {
      detail: { phase: 'ready', experiment: this.expName, previous: previousName },
    }));
    return this.qaWorkbenchSummary();
  }

  setEnvironmentPreset(id) {
    const nextId = normalizeEnvironmentPresetId(id);
    this.environmentPresetExplicit = true;
    this.environmentPresetId = nextId;
    if (!this.environmentScenarioExplicit || getEnvironmentScenario(this.environmentScenarioId).preset !== nextId) {
      this.environmentScenarioId = normalizeEnvironmentScenarioId(null, nextId);
      this.requestedEnvironmentScenarioId = null;
      this.environmentScenarioExplicit = false;
    }
    this.groundingMode = normalizeGroundingMode(
      this.groundingMode,
      ENVIRONMENT_PRESETS[nextId].grounding.allowedModes,
      ENVIRONMENT_PRESETS[nextId].grounding.defaultMode,
    );
    this.applyEnvironmentVisuals();
    this.dispatchEnvironmentChange();
    return this.qaEnvironmentSummary();
  }

  setGroundingMode(id) {
    const preset = ENVIRONMENT_PRESETS[this.environmentPresetId];
    this.requestedGroundingMode = id;
    this.groundingMode = normalizeGroundingMode(id, preset.grounding.allowedModes, preset.grounding.defaultMode);
    this.dispatchEnvironmentChange();
    return this.qaEnvironmentSummary();
  }

  dispatchEnvironmentChange() {
    window.dispatchEvent(new CustomEvent('robotics-lab-environment-change', {
      detail: this.qaEnvironmentSummary(),
    }));
  }

  clearEnvironmentVisuals() {
    if (!this.labVisualLayer) return;
    while (this.labVisualLayer.children.length > 0) {
      const child = this.labVisualLayer.children[0];
      this.labVisualLayer.remove(child);
      child.traverse?.((object) => {
        object.geometry?.dispose?.();
        if (Array.isArray(object.material)) {
          object.material.forEach((material) => material.dispose?.());
        } else {
          object.material?.dispose?.();
        }
      });
    }
  }

  applyEnvironmentVisuals() {
    if (!this.scene || !this.labVisualLayer) return;
    const summary = summarizeEnvironmentPreset(this.environmentPresetId, {
      scene: this.exp?.scene || this.params?.scene || null,
      groundingMode: this.groundingMode,
      requestedGroundingMode: this.requestedGroundingMode,
      defaultGroundingMode: inferGroundingModeFromExperiment(this.exp || {}),
    });
    this.clearEnvironmentVisuals();

    const styles = {
      "flat-lab": {
        background: 0x1f2933,
        fogNear: 16,
        fogFar: 30,
        ambient: 0.46,
        spot: 26,
        floor: 0x2c353d,
        gridColor: 0xb8c0c8,
        accent: 0x4fb3ff,
        marker: 0xffffff,
        wall: 0x202832,
        panel: 0x3b4650,
      },
      "instrumented-lab": {
        background: 0x0f171d,
        fogNear: 10,
        fogFar: 22,
        ambient: 0.34,
        spot: 34,
        floor: 0x111c24,
        gridColor: 0x22d3ee,
        accent: 0xf59e0b,
        marker: 0x67e8f9,
        wall: 0x101820,
        panel: 0x164e63,
      },
      "rough-terrain": {
        background: 0x1f241f,
        fogNear: 14,
        fogFar: 28,
        ambient: 0.40,
        spot: 30,
        floor: 0x24291f,
        gridColor: 0xa3e635,
        accent: 0xf97316,
        marker: 0xd9f99d,
        wall: 0x20251d,
        panel: 0x4d3d22,
      },
    };
    const style = styles[summary.preset] || styles["flat-lab"];

    const background = new THREE.Color(style.background);
    this.scene.background = background;
    this.scene.fog = new THREE.Fog(background, style.fogNear, style.fogFar);
    this.ambientLight.intensity = style.ambient * Math.PI;
    this.spotlight.intensity = style.spot * Math.PI;

    this.labVisualLayer.add(this.createLabBackdrop(style));
    this.loadAssetLabShell(style);

    const grid = new THREE.GridHelper(8, 32, style.gridColor, style.gridColor);
    grid.name = "Lab floor grid";
    grid.position.y = 0.045;
    grid.material.transparent = true;
    grid.material.opacity = summary.preset === "instrumented-lab" ? 0.38 : 0.26;
    grid.renderOrder = 1;
    this.labVisualLayer.add(grid);

    const axes = new THREE.AxesHelper(0.65);
    axes.name = "Lab origin axes";
    axes.position.set(0, 0.025, 0);
    this.labVisualLayer.add(axes);

    if (summary.visual.markers.includes("height bands")) {
      this.labVisualLayer.add(this.createHeightBands(style.marker));
    }
    if (summary.visual.markers.includes("curb lane")) {
      this.labVisualLayer.add(this.createTerrainLane(style.accent));
    }
    if (summary.visual.markers.includes("contact readouts")) {
      this.labVisualLayer.add(this.createContactReadoutRails(style.accent));
    }
    if (summary.preset === "flat-lab") {
      this.labVisualLayer.add(this.createCalibrationBay(style));
    }
    if (summary.preset === "instrumented-lab") {
      this.labVisualLayer.add(this.createMeasurementBay(style));
    }
    if (summary.preset === "rough-terrain") {
      this.labVisualLayer.add(this.createRoughTerrainRig(style));
    }

    this.appliedEnvironmentVisual = {
      preset: summary.preset,
      visualOnly: true,
      objects: this.labVisualLayer.children.map((child) => child.name || child.type),
      collision: "none-threejs-only",
      background: `#${style.background.toString(16).padStart(6, "0")}`,
      fog: { near: style.fogNear, far: style.fogFar },
    };
  }

  async loadAssetLabShell(style) {
    const token = ++this.labAssetLoadToken;
    const path = "assets/lab/lab_shell.gltf";
    this.labAssetLayerStatus = {
      path,
      loaded: false,
      loading: true,
      objectCount: 0,
      error: null,
    };
    try {
      if (!this.labAssetLoader) {
        const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
        this.labAssetLoader = new GLTFLoader();
      }
      const gltf = await this.labAssetLoader.loadAsync(path);
      if (token !== this.labAssetLoadToken || !this.labVisualLayer) return;
      const assetRoot = gltf.scene;
      assetRoot.name = "Asset backed lab shell";
      assetRoot.traverse((object) => {
        if (!object.isMesh) return;
        object.name = object.name || "Asset shell mesh";
        object.castShadow = false;
        object.receiveShadow = false;
        if (object.material) {
          object.material.transparent = true;
          object.material.depthWrite = false;
          object.material.opacity = Math.min(object.material.opacity ?? 1, 0.72);
          if (object.material.color) {
            object.material.color.lerp(new THREE.Color(style.panel), 0.18);
          }
        }
      });
      assetRoot.position.set(0, 0, 0);
      assetRoot.scale.setScalar(1);
      this.labVisualLayer.add(assetRoot);
      const objectCount = assetRoot.children.length || 1;
      this.labAssetLayerStatus = {
        path,
        loaded: true,
        loading: false,
        objectCount,
        error: null,
      };
      this.dispatchEnvironmentChange();
    } catch (error) {
      if (token !== this.labAssetLoadToken) return;
      this.labAssetLayerStatus = {
        path,
        loaded: false,
        loading: false,
        objectCount: 0,
        error: String(error?.message || error),
      };
      console.warn("lab shell asset load failed", error);
      this.dispatchEnvironmentChange();
    }
  }

  createLabBackdrop(style) {
    const group = new THREE.Group();
    group.name = "Selectable lab backdrop";

    const wallMaterial = new THREE.MeshStandardMaterial({
      color: style.wall,
      roughness: 0.9,
      metalness: 0.0,
      transparent: true,
      opacity: 0.82,
      side: THREE.DoubleSide,
    });
    const backWall = new THREE.Mesh(new THREE.PlaneGeometry(8, 2.4), wallMaterial);
    backWall.name = "Back lab wall";
    backWall.position.set(-2.3, 1.2, -3.0);
    backWall.rotation.y = Math.PI / 10;
    group.add(backWall);

    const sideWall = new THREE.Mesh(new THREE.PlaneGeometry(5, 2.0), wallMaterial.clone());
    sideWall.name = "Side lab wall";
    sideWall.position.set(-3.6, 1.0, -0.3);
    sideWall.rotation.y = Math.PI / 2;
    group.add(sideWall);

    const panelMaterial = new THREE.MeshBasicMaterial({
      color: style.panel,
      transparent: true,
      opacity: 0.42,
      side: THREE.DoubleSide,
    });
    for (const [index, x] of [-1.8, -0.9, 0].entries()) {
      const panel = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.95), panelMaterial.clone());
      panel.name = `Lab wall panel ${index + 1}`;
      panel.position.set(x, 1.25, -2.985);
      panel.rotation.y = Math.PI / 10;
      group.add(panel);
    }

    const railMaterial = new THREE.LineBasicMaterial({
      color: style.accent,
      transparent: true,
      opacity: 0.50,
    });
    const railGeometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-3.4, 0.03, -1.2),
      new THREE.Vector3(3.4, 0.03, -1.2),
      new THREE.Vector3(3.4, 0.03, 1.2),
      new THREE.Vector3(-3.4, 0.03, 1.2),
      new THREE.Vector3(-3.4, 0.03, -1.2),
    ]);
    const rail = new THREE.Line(railGeometry, railMaterial);
    rail.name = "Experiment boundary rail";
    group.add(rail);

    return group;
  }

  createCalibrationBay(style) {
    const group = new THREE.Group();
    group.name = "Calibration bay fixtures";

    const seamMaterial = new THREE.LineBasicMaterial({ color: style.marker, transparent: true, opacity: 0.24 });
    for (const x of [-2, -1, 1, 2]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x, 0.021, -2.4),
        new THREE.Vector3(x, 0.021, 2.4),
      ]);
      const seam = new THREE.Line(geometry, seamMaterial.clone());
      seam.name = "Calibration floor seam";
      group.add(seam);
    }

    const postMaterial = new THREE.MeshStandardMaterial({
      color: style.accent,
      roughness: 0.54,
      metalness: 0.18,
      transparent: true,
      opacity: 0.62,
    });
    for (const [x, z] of [[-1.45, -1.35], [1.45, -1.35], [-1.45, 1.35], [1.45, 1.35]]) {
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.42, 12), postMaterial.clone());
      post.name = "Calibration marker post";
      post.position.set(x, 0.21, z);
      group.add(post);
    }

    const stripeMaterial = new THREE.MeshBasicMaterial({ color: style.accent, transparent: true, opacity: 0.42 });
    for (const z of [-1.55, 1.55]) {
      const stripe = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 0.035), stripeMaterial.clone());
      stripe.name = "Calibration safety stripe";
      stripe.rotation.x = -Math.PI / 2;
      stripe.position.set(0, 0.024, z);
      group.add(stripe);
    }

    return group;
  }

  createHeightBands(color) {
    const group = new THREE.Group();
    group.name = "Lab height bands";
    const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.52 });
    for (const height of [0.4, 0.8, 1.2]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-1.1, height, -1.1),
        new THREE.Vector3(1.1, height, -1.1),
        new THREE.Vector3(1.1, height, 1.1),
        new THREE.Vector3(-1.1, height, 1.1),
        new THREE.Vector3(-1.1, height, -1.1),
      ]);
      const line = new THREE.Line(geometry, material.clone());
      line.name = `Height band ${height.toFixed(1)}m`;
      group.add(line);
    }
    return group;
  }

  createMeasurementBay(style) {
    const group = new THREE.Group();
    group.name = "Instrumented measurement bay";

    const frameMaterial = new THREE.MeshStandardMaterial({
      color: style.marker,
      roughness: 0.35,
      metalness: 0.42,
      transparent: true,
      opacity: 0.54,
    });
    const addBar = (name, position, scale) => {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(scale[0], scale[1], scale[2]), frameMaterial.clone());
      bar.name = name;
      bar.position.set(position[0], position[1], position[2]);
      group.add(bar);
      return bar;
    };
    addBar("Measurement gantry left upright", [-1.35, 0.78, -1.05], [0.035, 1.55, 0.035]);
    addBar("Measurement gantry right upright", [1.35, 0.78, -1.05], [0.035, 1.55, 0.035]);
    addBar("Measurement gantry top beam", [0, 1.55, -1.05], [2.75, 0.035, 0.035]);

    const sensorMaterial = new THREE.MeshStandardMaterial({
      color: style.accent,
      roughness: 0.46,
      metalness: 0.22,
      emissive: style.accent,
      emissiveIntensity: 0.12,
    });
    for (const [index, x] of [-1.2, 0, 1.2].entries()) {
      const sensor = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.10, 0.08), sensorMaterial.clone());
      sensor.name = `Overhead tracking sensor ${index + 1}`;
      sensor.position.set(x, 1.46, -0.98);
      group.add(sensor);
    }

    const monitorMaterial = new THREE.MeshBasicMaterial({ color: style.accent, transparent: true, opacity: 0.72, side: THREE.DoubleSide });
    for (const [index, z] of [-0.65, 0.05, 0.75].entries()) {
      const monitor = new THREE.Mesh(new THREE.PlaneGeometry(0.46, 0.24), monitorMaterial.clone());
      monitor.name = `Telemetry monitor ${index + 1}`;
      monitor.position.set(-2.18, 1.15, z);
      monitor.rotation.y = Math.PI / 2;
      group.add(monitor);
    }

    const cableMaterial = new THREE.LineBasicMaterial({ color: style.marker, transparent: true, opacity: 0.34 });
    for (const z of [-0.65, 0.05, 0.75]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-2.18, 0.78, z),
        new THREE.Vector3(-1.55, 0.78, z),
      ]);
      const cable = new THREE.Line(geometry, cableMaterial.clone());
      cable.name = "Instrument cable run";
      group.add(cable);
    }

    return group;
  }

  createTerrainLane(color) {
    const group = new THREE.Group();
    group.name = "Terrain test lane";
    const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.62 });
    for (const x of [-0.55, 0.55]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(x, 0.035, -2.3),
        new THREE.Vector3(x, 0.035, 2.3),
      ]);
      const line = new THREE.Line(geometry, material.clone());
      line.name = "Terrain lane edge";
      group.add(line);
    }
    return group;
  }

  createRoughTerrainRig(style) {
    const group = new THREE.Group();
    group.name = "Rough terrain test fixtures";

    const curbMaterial = new THREE.MeshStandardMaterial({
      color: style.panel,
      roughness: 0.86,
      metalness: 0.02,
      transparent: true,
      opacity: 0.78,
    });
    for (const [index, z] of [-1.25, -0.55, 0.15, 0.85].entries()) {
      const curb = new THREE.Mesh(new THREE.BoxGeometry(1.05, 0.10, 0.18), curbMaterial.clone());
      curb.name = `Visual curb block ${index + 1}`;
      curb.position.set(index % 2 === 0 ? -0.18 : 0.18, 0.055, z);
      group.add(curb);
    }

    const barrierMaterial = new THREE.MeshStandardMaterial({
      color: style.accent,
      roughness: 0.62,
      metalness: 0.10,
      transparent: true,
      opacity: 0.58,
    });
    for (const x of [-0.86, 0.86]) {
      const barrier = new THREE.Mesh(new THREE.BoxGeometry(0.055, 0.30, 3.2), barrierMaterial.clone());
      barrier.name = "Terrain side barrier";
      barrier.position.set(x, 0.15, -0.15);
      group.add(barrier);
    }

    const hazardMaterial = new THREE.MeshBasicMaterial({ color: style.accent, transparent: true, opacity: 0.64, side: THREE.DoubleSide });
    for (const [index, z] of [-1.7, 1.35].entries()) {
      const stripe = new THREE.Mesh(new THREE.PlaneGeometry(1.45, 0.06), hazardMaterial.clone());
      stripe.name = `Terrain hazard stripe ${index + 1}`;
      stripe.rotation.x = -Math.PI / 2;
      stripe.rotation.z = index === 0 ? 0.18 : -0.18;
      stripe.position.set(0, 0.032, z);
      group.add(stripe);
    }

    const boundaryMaterial = new THREE.LineBasicMaterial({ color: style.marker, transparent: true, opacity: 0.46 });
    for (const y of [0.18, 0.34]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-0.86, y, -1.75),
        new THREE.Vector3(0.86, y, -1.75),
        new THREE.Vector3(0.86, y, 1.45),
        new THREE.Vector3(-0.86, y, 1.45),
        new THREE.Vector3(-0.86, y, -1.75),
      ]);
      const line = new THREE.Line(geometry, boundaryMaterial.clone());
      line.name = "Terrain lane volume guide";
      group.add(line);
    }

    return group;
  }

  createContactReadoutRails(color) {
    const group = new THREE.Group();
    group.name = "Contact readout rails";
    const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.48 });
    for (const z of [-0.42, 0, 0.42]) {
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(-0.9, 0.03, z),
        new THREE.Vector3(0.9, 0.03, z),
      ]);
      const line = new THREE.Line(geometry, material.clone());
      line.name = "Contact readout rail";
      group.add(line);
    }
    return group;
  }

  addProjectOverlay() {
    const groups = [
      ['humanoids', 'Humanoids', ['g1-walk', 'g1-rough-walk', 'g1-controlled-squat', 'g1-decoupled-wbc-squat', 'g1-squat-reference-vs-wbc', 'unitree-g1-headless', 'unitree-g1-elastic-stand', 'g1-stand']],
      ['quadrupeds', 'Quadrupeds', ['barkour-walk', 'go1-walk', 'go1-rough-walk', 'spot-walk', 'spot-rough-walk', 'spot-stand']],
      ['arms', 'Arms / hands', ['so100-stack', 'panda-sweep', 'shadow-hand']],
      ['checks', 'Harness checks', ['dummy-arm', 'humanoid-settle']],
    ];
    const experimentCopy = {
      'g1-walk': {
        name: 'Unitree G1',
        kind: 'Humanoid',
        model: 'Floating-base 29-DOF MuJoCo model',
        source: 'MuJoCo Playground policy bundle',
        mode: 'Learned policy',
        status: 'Verified walking',
        description: 'Full-body humanoid walking controlled by a neural policy running closed-loop in the browser.',
        actions: ['Walk forward', 'Strafe', 'Turn', 'Drag recovery'],
        evidence: ['ONNX parity', 'native rollout', 'browser byte-parity', 'live QA'],
        limit: 'This is locomotion, not a squat or acrobatic skill.',
      },
      'g1-rough-walk': {
        name: 'Unitree G1 Rough',
        kind: 'Humanoid',
        model: 'Floating-base 29-DOF MuJoCo model',
        source: 'G1 policy on rough curb scene',
        mode: 'Learned policy',
        status: 'Robustness check',
        description: 'The G1 walking policy is placed on low curb terrain to expose terrain and command robustness.',
        actions: ['Walk over curbs', 'Turn', 'Command sweep'],
        evidence: ['rough terrain scene', 'command sweep', 'live QA'],
        limit: 'Terrain robustness does not prove named skills such as squat, kick, or jump.',
      },
      'g1-controlled-squat': {
        name: 'Unitree G1 Lowering Probe',
        kind: 'Humanoid',
        model: 'Floating-base 29-DOF MuJoCo model',
        source: 'exp28/29/30 controller audit',
        mode: 'Replay / probe',
        status: 'Not a squat',
        description: 'A shallow lowering trajectory from the G1 controller audit. It is useful evidence, but visually it is only a micro-dip.',
        actions: ['Replay probe', 'Compare posture', 'Audit depth'],
        evidence: ['6s no-fall', 'about 1cm pelvis dip', 'visible-squat gate failed'],
        limit: 'Squat remains paused until pelvis drop, knee flexion, hip pitch, and no-fall gates pass together.',
      },
      'g1-decoupled-wbc-squat': {
        name: 'Unitree G1 Visible Squat',
        kind: 'Humanoid',
        model: 'Floating-base 29-DOF MuJoCo model',
        source: 'GR00T Decoupled WBC Balance ONNX',
        mode: 'Measured WBC replay',
        status: 'Native + browser gate',
        description: 'A measured MuJoCo qpos trace from a Decoupled WBC height-command squat schedule, replayed through the same browser trajectory contract.',
        actions: ['Replay squat', 'Inspect posture', 'Compare micro-dip'],
        evidence: ['11.6cm pelvis drop', 'knee 0.707rad', 'hip 0.427rad', 'contact 1.00', 'foot slip 0.003m', 'browser QA'],
        limit: 'This is a kinematic browser replay of a measured simulation trace, not real robot telemetry.',
      },
      'g1-squat-reference-vs-wbc': {
        name: 'G1 Reference vs Rollout',
        kind: 'Motion comparison',
        model: 'Floating-base 29-DOF MuJoCo model',
        source: 'M22 compiled reference + measured WBC rollout',
        mode: 'Comparison replay',
        status: 'Viewer gate',
        description: 'A browser comparison between the M22 squat reference trajectory and the measured WBC rollout that passed the visible squat gate.',
        actions: ['Scrub rollout frame', 'Compare height error', 'Compare lower-body joint RMS'],
        evidence: ['reference qpos contract', 'WBC rollout', 'qaCompare PASS'],
        limit: 'This compares a reference target against a measured simulation trace. It is not a learned policy success claim.',
      },
      'unitree-g1-headless': {
        name: 'Unitree G1 Backend Bridge',
        kind: 'Humanoid',
        model: 'Official Unitree G1 29-DOF MJCF',
        source: 'unitreerobotics/unitree_mujoco headless MuJoCo trace',
        mode: 'Backend replay / bridge',
        status: 'Bridge verified',
        description: 'A qpos replay exported from the official Unitree MuJoCo G1 scene and loaded through the existing web twin contract.',
        actions: ['Replay backend trace', 'Inspect qpos contract', 'Compare stability'],
        evidence: ['Unitree source layout PASS', 'nq=36/nu=29 runtime load', 'web contract PASS'],
        limit: 'This proves backend-to-viewer wiring, not a stable controller; the PD hold trace collapses during replay.',
      },
      'unitree-g1-elastic-stand': {
        name: 'Unitree G1 Assisted Stand',
        kind: 'Humanoid',
        model: 'Official Unitree G1 29-DOF MJCF',
        source: 'unitreerobotics/unitree_mujoco headless MuJoCo + elastic band',
        mode: 'Backend replay / assisted stream',
        status: 'Stable fixture',
        description: 'A stable standing backend trace generated from the official Unitree G1 scene with the same elastic-band support option exposed in Unitree simulator examples.',
        actions: ['Replay stable stand', 'Inspect telemetry', 'Stream qpos frames'],
        evidence: ['root drop 0.096mm', 'web contract PASS', 'telemetry sidecar PASS'],
        limit: 'This is an assisted digital-twin fixture, not proof of an unassisted humanoid standing controller.',
      },
      'barkour-walk': {
        name: 'Google Barkour',
        kind: 'Quadruped',
        model: 'Floating-base quadruped',
        source: 'MuJoCo Playground Barkour task',
        mode: 'Learned policy',
        status: 'Verified walking',
        description: 'A compact quadruped policy with observation history, added through the policy ingestion routine.',
        actions: ['Walk forward', 'Strafe', 'Turn'],
        evidence: ['training log', 'ONNX parity', 'native rollout', 'live QA'],
        limit: 'Locomotion baseline only; not an object-contact skill.',
      },
      'go1-walk': {
        name: 'Unitree Go1',
        kind: 'Quadruped',
        model: 'Floating-base 12-actuator Go1',
        source: 'MuJoCo Playground policy bundle',
        mode: 'Learned policy',
        status: 'Verified walking',
        description: 'A four-legged robot policy running directly in WebAssembly with live joystick commands.',
        actions: ['Walk forward', 'Strafe', 'Turn', 'Drag test'],
        evidence: ['training log', 'ONNX parity', 'native rollout', 'live QA'],
        limit: 'Shows policy deployment and interaction, not manipulation.',
      },
      'go1-rough-walk': {
        name: 'Unitree Go1 Rough',
        kind: 'Quadruped',
        model: 'Floating-base 12-actuator Go1',
        source: 'Go1 policy on rough curb scene',
        mode: 'Learned policy',
        status: 'Robustness check',
        description: 'Go1 locomotion checked on rough curb scenes and command changes.',
        actions: ['Walk over curbs', 'Command sweep', 'Drag test'],
        evidence: ['rough terrain scene', 'command sweep', 'live QA'],
        limit: 'Terrain coverage is limited to the bundled curb scenes.',
      },
      'spot-walk': {
        name: 'Boston Dynamics Spot',
        kind: 'Quadruped',
        model: 'Floating-base Spot model',
        source: 'MuJoCo Playground policy bundle',
        mode: 'Learned policy',
        status: 'Verified walking',
        description: 'A Spot model driven by a live closed-loop policy and browser joystick command.',
        actions: ['Walk forward', 'Strafe', 'Turn', 'Drag test'],
        evidence: ['ONNX parity', 'native rollout', 'browser parity', 'live QA'],
        limit: 'Public demo uses simulation only.',
      },
      'spot-rough-walk': {
        name: 'Spot Rough',
        kind: 'Quadruped',
        model: 'Floating-base Spot model',
        source: 'Spot policy on rough curb scene',
        mode: 'Learned policy',
        status: 'Robustness check',
        description: 'Spot policy tested against curb terrain and command changes.',
        actions: ['Walk over curbs', 'Command sweep', 'Drag test'],
        evidence: ['rough terrain scene', 'command sweep', 'live QA'],
        limit: 'Robustness check, not sim-to-real proof.',
      },
      'so100-stack': {
        name: 'SO-100',
        kind: 'Robot arm',
        model: 'Low-cost fixed-base arm',
        source: 'SO-100 MuJoCo scene and recorded trajectory',
        mode: 'Scripted replay',
        status: 'Verified replay',
        description: 'A low-cost arm digital twin replaying a three-block pick-and-place task.',
        actions: ['Replay stack', 'Drag objects', 'Teleop gripper'],
        evidence: ['three-block stack', 'IK residual check', 'browser replay QA'],
        limit: 'This is scripted control, not learned manipulation.',
      },
      'panda-sweep': {
        name: 'Franka Panda',
        kind: 'Robot arm',
        model: '7-DOF fixed-base arm',
        source: 'MuJoCo Menagerie style scene',
        mode: 'Scripted control',
        status: 'Control baseline',
        description: 'A 7-DOF arm scene for joint motion and teleop checks.',
        actions: ['Replay joint sweep', 'Teleop end-effector'],
        evidence: ['joint sweep replay', 'teleop check'],
        limit: 'Used as an embodiment/control baseline.',
      },
      'shadow-hand': {
        name: 'Shadow Hand',
        kind: 'Dexterous hand',
        model: 'Dexterous hand scene',
        source: 'MuJoCo hand model',
        mode: 'Scripted replay',
        status: 'Replay baseline',
        description: 'A hand model replaying finger flexion and contact-ready motion.',
        actions: ['Replay finger curl', 'Inspect joints'],
        evidence: ['finger curl replay', 'joint visualization'],
        limit: 'No learned dexterous policy is claimed.',
      },
      'dummy-arm': {
        name: 'Dummy 2-link arm',
        kind: 'Harness check',
        model: 'Minimal 2-link arm',
        source: 'Local regression scene',
        mode: 'Replay',
        status: 'Registry check',
        description: 'A small test arm used to prove new scenes can be added cleanly.',
        actions: ['Replay motion', 'Scene loading check'],
        evidence: ['zero-code registry add', 'replay QA'],
        limit: 'Validation fixture only.',
      },
      'g1-stand': {
        name: 'Unitree G1 Stand',
        kind: 'Model check',
        model: 'Floating-base 29-DOF MuJoCo model',
        source: 'G1 settle scene',
        mode: 'Physics check',
        status: 'Settle check',
        description: 'The G1 model settling under physics without the walking policy.',
        actions: ['Settle', 'Drag test', 'Inspect posture'],
        evidence: ['model loads', 'settle replay', 'drag interaction'],
        limit: 'No policy or skill is running.',
      },
      'spot-stand': {
        name: 'Spot Stand',
        kind: 'Model check',
        model: 'Floating-base Spot model',
        source: 'Spot settle scene',
        mode: 'Physics check',
        status: 'Settle check',
        description: 'Spot model settling under physics.',
        actions: ['Settle', 'Drag test'],
        evidence: ['model loads', 'settle replay'],
        limit: 'No policy or skill is running.',
      },
      'humanoid-settle': {
        name: 'Humanoid',
        kind: 'Model check',
        model: 'Generic humanoid scene',
        source: 'MuJoCo example scene',
        mode: 'Physics check',
        status: 'Platform check',
        description: 'A generic humanoid scene used to validate the platform.',
        actions: ['Settle', 'Drag test'],
        evidence: ['scene load', 'settle replay'],
        limit: 'General loader coverage, not G1 evidence.',
      },
    };
    const panel = document.createElement('section');
    panel.className = 'project-panel';
    panel.innerHTML = `
      <div class="project-panel__head">
        <div>
          <div class="project-panel__eyebrow">Browser robotics lab</div>
          <div class="project-panel__brand">Robotics Lab</div>
          <div class="project-panel__domain">Live MuJoCo twins, policies, and replay probes</div>
        </div>
        <button class="project-panel__toggle" type="button" aria-expanded="true" title="Collapse panel">-</button>
      </div>
      <div class="project-panel__body">
        <div class="lab-status">
          <span>Live physics</span>
          <span>Policy gallery</span>
          <span>Squat paused</span>
        </div>
        <div class="robot-picker__label">Robot selection</div>
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
          <div class="robot-card__topline">
            <span class="robot-card__mode"></span>
            <span class="robot-card__status"></span>
          </div>
          <div class="robot-card__label">Robot description</div>
          <div class="robot-card__description"></div>
          <div class="robot-card__facts">
            <div>
              <span>Model</span>
              <strong class="robot-card__model"></strong>
            </div>
            <div>
              <span>Source</span>
              <strong class="robot-card__source"></strong>
            </div>
          </div>
          <div class="robot-card__section twin-workbench">
            <div class="robot-card__label">Twin workbench</div>
            <div class="twin-workbench__grid">
              <div>
                <span>Runtime</span>
                <strong data-workbench="runtime"></strong>
              </div>
              <div>
                <span>State</span>
                <strong data-workbench="state"></strong>
              </div>
              <div>
                <span>Evidence</span>
                <strong data-workbench="evidence"></strong>
              </div>
              <div>
                <span>Gate</span>
                <strong data-workbench="gate"></strong>
              </div>
            </div>
          </div>
          <div class="robot-card__section">
            <div class="robot-card__label">Available motions</div>
            <div class="robot-card__chips robot-card__actions"></div>
          </div>
          <div class="robot-card__section">
            <div class="robot-card__label">Evidence</div>
            <div class="robot-card__chips robot-card__evidence"></div>
          </div>
          <div class="robot-card__section">
            <div class="robot-card__label">Current limit</div>
            <div class="robot-card__limit"></div>
          </div>
          <div class="robot-card__section robot-card__telemetry-section">
            <div class="robot-card__label">Telemetry frame</div>
            <div class="telemetry-readout" aria-live="polite">
              <span data-telemetry="frame"></span>
              <span data-telemetry="tick"></span>
              <span data-telemetry="height"></span>
              <span data-telemetry="jointVel"></span>
            </div>
          </div>
          <div class="robot-card__section robot-card__compare-section">
            <div class="robot-card__label">Reference vs rollout</div>
            <div class="compare-readout" aria-live="polite">
              <span data-compare="frame"></span>
              <span data-compare="height"></span>
              <span data-compare="joints"></span>
              <span data-compare="labels"></span>
            </div>
          </div>
        </div>
        <div class="research-card">
          <div class="research-card__label">Lab direction</div>
          <div class="research-card__title">Show verified capability, not experiment numbers</div>
          <div class="research-card__text">The public surface is organized by robot, motion, and evidence. G1 squat research is paused until visible-depth and no-fall gates both pass.</div>
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
        width: min(404px, calc(100vw - 28px));
        color: #f8fafc;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: rgba(10, 14, 18, 0.84);
        border: 1px solid rgba(255,255,255,0.14);
        box-shadow: 0 20px 70px rgba(0,0,0,0.36);
        backdrop-filter: blur(16px);
        border-radius: 8px;
        overflow: visible;
      }
      .project-panel, .project-panel * { box-sizing: border-box; }
      .project-panel__head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 14px 15px 12px;
        border-bottom: 1px solid rgba(255,255,255,0.12);
      }
      .project-panel__eyebrow {
        margin-bottom: 4px;
        color: rgba(248,250,252,0.52);
        font-size: 10px;
        line-height: 1.2;
        font-weight: 760;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }
      .project-panel__brand {
        font-size: 17px;
        line-height: 1.15;
        font-weight: 780;
      }
      .project-panel__domain {
        margin-top: 3px;
        color: rgba(248,250,252,0.64);
        font-size: 12px;
        line-height: 1.2;
      }
      .project-panel__toggle {
        width: 28px;
        height: 28px;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 6px;
        color: #f8fafc;
        background: rgba(255,255,255,0.08);
        font: 700 16px/1 ui-sans-serif, system-ui, sans-serif;
        cursor: pointer;
      }
      .project-panel__body {
        padding: 13px 14px 14px;
        border-radius: 0 0 8px 8px;
        background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0));
      }
      .lab-status {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 6px;
        margin-bottom: 12px;
      }
      .lab-status span {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 28px;
        padding: 0 7px;
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 6px;
        background: rgba(255,255,255,0.055);
        color: rgba(248,250,252,0.76);
        font-size: 10px;
        line-height: 1.15;
        font-weight: 720;
        text-align: center;
      }
      .robot-picker {
        position: relative;
      }
      .robot-picker__label {
        margin: 0 0 7px;
        color: rgba(248,250,252,0.58);
        font-size: 11px;
        line-height: 1.2;
        font-weight: 760;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .robot-picker__button {
        width: 100%;
        min-height: 52px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 6px;
        padding: 8px 10px;
        color: #f8fafc;
        background: rgba(2,6,10,0.62);
        text-align: left;
        cursor: pointer;
      }
      .robot-picker__name {
        display: block;
        font-size: 15px;
        line-height: 1.2;
        font-weight: 750;
      }
      .robot-picker__kind {
        display: block;
        margin-top: 3px;
        color: rgba(248,250,252,0.62);
        font-size: 12px;
        line-height: 1.2;
      }
      .robot-picker__chevron {
        color: rgba(248,250,252,0.7);
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
        z-index: 2;
        background: #090f14;
        box-shadow: 0 18px 50px rgba(0,0,0,0.42);
      }
      .robot-picker.is-open .robot-picker__menu { display: block; }
      .robot-picker.is-open ~ .robot-card,
      .robot-picker.is-open ~ .research-card { visibility: hidden; }
      .robot-picker__group {
        margin: 8px 4px 5px;
        color: rgba(248,250,252,0.48);
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
        color: #f8fafc;
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
        color: rgba(248,250,252,0.54);
        font-size: 11px;
      }
      .robot-card {
        margin-top: 12px;
        padding: 12px;
        border: 1px solid rgba(255,255,255,0.11);
        border-radius: 8px;
        background: rgba(255,255,255,0.04);
      }
      .robot-card__topline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 10px;
      }
      .robot-card__mode,
      .robot-card__status {
        display: inline-flex;
        align-items: center;
        min-height: 24px;
        padding: 0 8px;
        border-radius: 999px;
        font-size: 11px;
        line-height: 1;
        font-weight: 760;
      }
      .robot-card__mode {
        color: #dbeafe;
        border: 1px solid rgba(147,197,253,0.28);
        background: rgba(37,99,235,0.18);
      }
      .robot-card__status {
        color: #e2e8f0;
        border: 1px solid rgba(226,232,240,0.18);
        background: rgba(15,23,42,0.34);
      }
      .robot-card__description {
        color: rgba(248,250,252,0.88);
        font-size: 13px;
        line-height: 1.45;
      }
      .robot-card__facts {
        display: grid;
        gap: 7px;
        margin-top: 11px;
      }
      .robot-card__facts div {
        display: grid;
        grid-template-columns: 58px 1fr;
        gap: 8px;
        align-items: baseline;
      }
      .robot-card__facts span {
        color: rgba(248,250,252,0.48);
        font-size: 11px;
        line-height: 1.2;
        font-weight: 760;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
      .robot-card__facts strong {
        color: rgba(248,250,252,0.82);
        font-size: 12px;
        line-height: 1.35;
        font-weight: 650;
      }
      .robot-card__section {
        margin-top: 11px;
      }
      .robot-card__label,
      .research-card__label {
        margin-bottom: 6px;
        color: rgba(248,250,252,0.54);
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
        color: #f8fafc;
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 999px;
        background: rgba(255,255,255,0.07);
        font-size: 11px;
        line-height: 1;
      }
      .robot-card__limit,
      .research-card__text {
        color: rgba(248,250,252,0.76);
        font-size: 12px;
        line-height: 1.45;
      }
      .robot-card__evidence .robot-card__chip {
        color: rgba(248,250,252,0.82);
        border-color: rgba(134,239,172,0.20);
        background: rgba(22,101,52,0.16);
      }
      .twin-workbench__grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 7px;
      }
      .twin-workbench__grid div {
        min-height: 54px;
        padding: 8px;
        border-radius: 7px;
        border: 1px solid rgba(125,211,252,0.16);
        background: rgba(8,47,73,0.20);
      }
      .twin-workbench__grid span {
        display: block;
        margin-bottom: 5px;
        color: rgba(248,250,252,0.50);
        font-size: 10px;
        line-height: 1.1;
        font-weight: 780;
        letter-spacing: 0.05em;
        text-transform: uppercase;
      }
      .twin-workbench__grid strong {
        display: block;
        color: rgba(248,250,252,0.88);
        font-size: 11px;
        line-height: 1.25;
        font-weight: 690;
      }
      .robot-card__telemetry-section {
        display: none;
      }
      .project-panel.has-telemetry .robot-card__telemetry-section {
        display: block;
      }
      .robot-card__compare-section {
        display: none;
      }
      .project-panel.has-compare .robot-card__compare-section {
        display: block;
      }
      .telemetry-readout,
      .compare-readout {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 6px;
      }
      .telemetry-readout span,
      .compare-readout span {
        min-height: 25px;
        padding: 6px 7px;
        border-radius: 6px;
        color: rgba(248,250,252,0.82);
        border: 1px solid rgba(147,197,253,0.18);
        background: rgba(30,64,175,0.14);
        font-size: 11px;
        line-height: 1.15;
        font-weight: 650;
      }
      .research-card {
        margin-top: 13px;
        padding: 12px;
        border-radius: 8px;
        background: rgba(31, 44, 54, 0.72);
        border: 1px solid rgba(255,255,255,0.10);
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
          max-height: 60vh;
          overflow: auto;
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
    const mode = panel.querySelector('.robot-card__mode');
    const status = panel.querySelector('.robot-card__status');
    const model = panel.querySelector('.robot-card__model');
    const source = panel.querySelector('.robot-card__source');
    const actions = panel.querySelector('.robot-card__actions');
    const evidence = panel.querySelector('.robot-card__evidence');
    const limit = panel.querySelector('.robot-card__limit');
    this.workbenchEls = {
      runtime: panel.querySelector('[data-workbench="runtime"]'),
      state: panel.querySelector('[data-workbench="state"]'),
      evidence: panel.querySelector('[data-workbench="evidence"]'),
      gate: panel.querySelector('[data-workbench="gate"]'),
    };
    this.telemetryEls = {
      frame: panel.querySelector('[data-telemetry="frame"]'),
      tick: panel.querySelector('[data-telemetry="tick"]'),
      height: panel.querySelector('[data-telemetry="height"]'),
      jointVel: panel.querySelector('[data-telemetry="jointVel"]'),
    };
    this.compareEls = {
      frame: panel.querySelector('[data-compare="frame"]'),
      height: panel.querySelector('[data-compare="height"]'),
      joints: panel.querySelector('[data-compare="joints"]'),
      labels: panel.querySelector('[data-compare="labels"]'),
    };
    if (this.telemetry || this.streamStats?.enabled) {
      panel.classList.add('has-telemetry');
      this.updateTelemetryPanel(0);
    }
    if (this.compare) {
      panel.classList.add('has-compare');
      this.updateComparePanel(0);
    }
    const metaFor = (key) => experimentCopy[key] || {
      name: key,
      kind: this.registry.experiments[key]?.policy ? 'Policy' : 'Replay',
      model: 'Registered MuJoCo embodiment',
      source: this.registry.experiments[key]?.scene || 'experiments.json',
      mode: this.registry.experiments[key]?.policy ? 'Learned policy' : 'Replay',
      status: 'Registered',
      description: this.registry.experiments[key]?.title || key,
      actions: ['Inspect scene'],
      evidence: ['registry entry'],
      limit: 'No public evidence summary has been written yet.',
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
    this.currentMeta = currentMeta;
    pickerName.textContent = currentMeta.name;
    pickerKind.textContent = currentMeta.kind;
    mode.textContent = currentMeta.mode;
    status.textContent = currentMeta.status;
    description.textContent = currentMeta.description;
    model.textContent = currentMeta.model;
    source.textContent = currentMeta.source;
    limit.textContent = currentMeta.limit;
    this.updateWorkbenchPanel(currentMeta);
    for (const action of currentMeta.actions) {
      const chip = document.createElement('span');
      chip.className = 'robot-card__chip';
      chip.textContent = action;
      actions.appendChild(chip);
    }
    for (const proof of currentMeta.evidence) {
      const chip = document.createElement('span');
      chip.className = 'robot-card__chip';
      chip.textContent = proof;
      evidence.appendChild(chip);
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
    panel.hidden = true;
    panel.dataset.legacyProjectPanel = 'true';
    this.container.appendChild(panel);
  }

  workbenchSummary(meta = null) {
    meta = meta || this.currentMeta || null;
    const exp = this.exp || {};
    const lanes = [];
    const runtime = this.policy
      ? 'browser ONNX policy'
      : (this.streamStats?.enabled ? 'DDS/WebSocket stream' : 'trajectory replay');
    if (this.policy) lanes.push('closed-loop policy');
    if (this.replayQpos) lanes.push('qpos replay');
    if (this.telemetry || exp.telemetry_sidecar) lanes.push('telemetry sidecar');
    if (this.compare || exp.compare_trajectory) lanes.push('reference compare');
    if (this.streamStats?.enabled) lanes.push('live stream');
    if (exp.teleop) lanes.push('teleop');

    const frameCount = this.replayN || null;
    const fps = this.replayFps || (exp.policy?.ctrl_dt ? Math.round(1 / exp.policy.ctrl_dt) : null);
    const stateContract = {
      format: this.streamStats?.enabled ? 'physical-ai-stream-frame-v0' : 'physical-ai-web-trajectory-v1',
      scene: exp.scene || null,
      nq: this.model?.nq ?? null,
      nu: this.model?.nu ?? null,
      frames: frameCount,
      fps,
      telemetry: Boolean(this.telemetry || exp.telemetry_sidecar),
      comparison: Boolean(this.compare || exp.compare_trajectory),
    };
    const gate = this.compare
      ? 'qaCompare'
      : (this.streamStats?.enabled ? 'qaStreamStatus' : (this.policy ? 'qaStep' : 'qaSeek'));
    const summary = {
      experiment: this.expName,
      title: exp.title || this.expName,
      runtime,
      stateContract,
      control: this.controlSummary(),
      physicsReadout: this.physicsReadoutSummary(),
      environment: this.qaEnvironmentSummary(),
      evidenceLanes: lanes,
      gate,
      status: meta?.status || null,
      limit: meta?.limit || null,
    };
    summary.pass = Boolean(
      summary.experiment &&
      summary.runtime &&
      summary.stateContract.scene &&
      summary.stateContract.nq > 0 &&
      summary.evidenceLanes.length > 0 &&
      summary.gate
    );
    return summary;
  }

  controlSummary() {
    const mapping = {
      ArrowUp: 'vx + forward',
      W: 'vx + forward',
      ArrowDown: 'vx - backward',
      S: 'vx - backward',
      ArrowLeft: 'vy + left',
      A: 'vy + left',
      ArrowRight: 'vy - right',
      D: 'vy - right',
      Q: 'vyaw + turn left',
      E: 'vyaw - turn right',
    };
    if (!this.policy || !this.pol) {
      return {
        enabled: false,
        command: null,
        range: null,
        inputSource: 'unavailable',
        heldCommands: [],
        mapping,
        claimLevel: 'not-policy-mode',
      };
    }
    return {
      enabled: true,
      command: Array.from(this.pol.command || [0, 0, 0]),
      range: this.commandRange || this.pol.cmdRange || null,
      inputSource: this.lastCommandInputSource || 'initial',
      heldCommands: Array.from(this.commandHeld || []),
      mapping,
      claimLevel: 'policy-command-input',
      note: 'Browser policy command input, not real robot telemetry.',
    };
  }

  summarizeRuntimeField(name, value) {
    const unavailable = {
      name,
      supported: false,
      type: typeof value,
      length: null,
      sample: null,
    };
    if (value === undefined || value === null) return unavailable;
    if (typeof value === 'number' || typeof value === 'boolean') {
      return {
        name,
        supported: true,
        type: typeof value,
        length: null,
        sample: value,
      };
    }
    if (ArrayBuffer.isView(value) || Array.isArray(value)) {
      const length = value.length ?? null;
      return {
        name,
        supported: true,
        type: value.constructor?.name || typeof value,
        length,
        sample: Array.from(value).slice(0, 12),
      };
    }
    if (typeof value === 'object') {
      const keys = Object.keys(value).slice(0, 12);
      return {
        name,
        supported: true,
        type: value.constructor?.name || 'object',
        length: keys.length,
        sample: keys,
      };
    }
    return {
      name,
      supported: true,
      type: typeof value,
      length: null,
      sample: String(value),
    };
  }

  physicsReadoutSummary() {
    const fields = ['ncon', 'contact', 'cfrc_ext', 'sensordata'];
    const data = this.data || null;
    const auditedFields = fields.map((name) => this.summarizeRuntimeField(name, data?.[name]));
    const supported = auditedFields.filter((field) => field.supported).map((field) => field.name);
    const unavailable = auditedFields.filter((field) => !field.supported).map((field) => field.name);
    return {
      enabled: Boolean(data),
      readOnly: true,
      claimLevel: supported.length ? 'browser-runtime-readout-probe' : 'unsupported-browser-readout-probe',
      auditedFields,
      supported,
      unavailable,
      contactCount: typeof data?.ncon === 'number' ? data.ncon : null,
      note: 'Read-only MuJoCo WASM runtime probe; unsupported fields are not replaced with visual cues.',
    };
  }

  dispatchControlChange() {
    window.dispatchEvent(new CustomEvent('robotics-lab-control-change', {
      detail: {
        experiment: this.expName,
        control: this.controlSummary(),
      },
    }));
  }

  updateWorkbenchPanel(meta) {
    if (!this.workbenchEls) return;
    const summary = this.workbenchSummary(meta);
    this.workbenchEls.runtime.textContent = summary.runtime;
    this.workbenchEls.state.textContent = `qpos[${summary.stateContract.nq}]` +
      (summary.stateContract.frames ? ` · ${summary.stateContract.frames} frames` : '');
    this.workbenchEls.evidence.textContent = summary.evidenceLanes.join(' · ');
    this.workbenchEls.gate.textContent = summary.gate;
  }

  qaWorkbenchSummary() {
    return this.workbenchSummary();
  }

  qaEnvironmentSummary() {
    const terrainGeoms = this.getTerrainGeomNames();
    const obstacleGeoms = this.getObstacleGeomNames();
    const contactBearingTerrain = terrainGeoms.length > 0 && /rough|curb|obstacle/i.test(this.exp?.scene || this.params?.scene || "");
    const summary = summarizeEnvironmentPreset(this.environmentPresetId, {
      scene: this.exp?.scene || this.params?.scene || null,
      groundingMode: this.groundingMode,
      requestedGroundingMode: this.requestedGroundingMode,
      defaultGroundingMode: inferGroundingModeFromExperiment(this.exp || {}),
      contactBearingTerrain,
      terrainGeomCount: terrainGeoms.length,
      terrainGeomNames: terrainGeoms,
    });
    const scenario = summarizeEnvironmentScenario(this.environmentScenarioId, {
      preset: this.environmentPresetId,
      scene: this.exp?.scene || this.params?.scene || null,
      contactBearingTerrain,
      terrainGeomCount: terrainGeoms.length,
      terrainGeomNames: terrainGeoms,
      obstacleGeomCount: obstacleGeoms.length,
      obstacleGeomNames: obstacleGeoms,
    });
    summary.scenario = scenario;
    if (summary.preset === "rough-terrain" && contactBearingTerrain) {
      summary.claimLevel = "contact-bearing-scene";
      summary.scene.mode = "active-rough-scene-variant";
      summary.scene.reloadRequired = false;
      summary.scene.mutation = "active-scene";
      summary.physicsProfile = {
        ...summary.physicsProfile,
        state: "active-contact-bearing-scene",
        runtimeChanges: true,
      };
      summary.changedRuntime = true;
    }
    summary.visualLayer = this.appliedEnvironmentVisual || null;
    summary.assetLayer = this.labAssetLayerStatus || null;
    summary.availablePresets = Object.keys(ENVIRONMENT_PRESETS);
    summary.availableScenarios = Object.keys(ENVIRONMENT_SCENARIOS);
    summary.availableEpisodeProfiles = Object.keys(EPISODE_RANDOMIZATION_PROFILES);
    summary.availableComparisonProfiles = Object.keys(EPISODE_COMPARISON_PROFILES);
    summary.episodeRandomization = summarizeEpisodeRandomizationProfile(this.episodeRandomizationProfileId);
    summary.episodeComparison = summarizeEpisodeComparisonProfile(this.episodeComparisonProfileId);
    summary.pass = Boolean(
      summary.preset &&
      summary.availablePresets.includes(summary.preset) &&
      summary.scenario?.pass &&
      summary.scenario?.preset === summary.preset &&
      summary.scene.activeScene &&
      summary.floor.profile &&
      summary.contactProfile.intent &&
      summary.groundingMode &&
      summary.physicsProfile.state &&
      summary.visualLayer?.visualOnly === true &&
      summary.visualLayer?.collision === "none-threejs-only" &&
      GROUNDING_MODES[summary.groundingMode] &&
      summary.episodeRandomization?.id &&
      summary.episodeComparison?.id &&
      summary.groundingControl?.behaviorMutation === false
    );
    return summary;
  }

  getTerrainGeomNames() {
    if (!this.model?.name_geomadr || !this.model?.names) return [];
    const textDecoder = new TextDecoder("utf-8");
    const nullChar = textDecoder.decode(new ArrayBuffer(1));
    const names = [];
    for (let i = 0; i < this.model.ngeom; i++) {
      const name = textDecoder.decode(this.model.names.subarray(this.model.name_geomadr[i])).split(nullChar)[0];
      if (/^(curb_|step_|terrain_)/i.test(name)) names.push(name);
    }
    return names;
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
      lines.unshift(coarse ? '슬라이더로 조종 (vx/vy/vyaw)' : '방향키/WASD 이동 · Q/E 회전 · Space 일시정지');
    }
    if (this.teleopCfg) {
      lines.push('🤏 Teleop 켠 뒤 ' + (coarse ? '끌기' : '드래그') + ' = 팔 끝 IK 조종');
    }
    hint.innerHTML = lines.join('<br>');
    this.controlHintEl = hint;
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
      n_substeps: p.n_substeps, command: [0, 0, 0],
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
    const runId = this.policyRunId || 0;
    this.runPolicyLoop(runId);
  }

  // Interactive joystick: bind the velocity command [vx, vy, vyaw] to GUI sliders. This is a
  // joystick-conditioned policy (command is part of the obs), so dragging a slider steers the
  // live robot — buildPolicyObs reads this.pol.command in place every control step.
  addCommandGUI() {
    const c = this.pol.command;
    const r = this.pol.cmdRange || { vx: [-1.0, 1.5], vy: [-0.8, 0.8], vyaw: [-1.5, 1.5] };
    this.commandRange = r;
    const f = this.gui.addFolder('Command (drag, arrows, or WASD/QE to steer)');
    this.cmdControllers = [
      f.add(c, '0', r.vx[0], r.vx[1], 0.05).name('vx  forward'),
      f.add(c, '1', r.vy[0], r.vy[1], 0.05).name('vy  strafe'),
      f.add(c, '2', r.vyaw[0], r.vyaw[1], 0.05).name('vyaw  turn'),
    ];
    for (const ctl of this.cmdControllers) {
      ctl.onChange(() => {
        this.lastCommandInputSource = 'slider';
        this.commandHeld.clear();
        this.dispatchControlChange();
      });
    }
    f.open();
    this.bindCommandKeys(r);
  }

  getObstacleGeomNames() {
    if (!this.model?.name_geomadr || !this.model?.names) return [];
    const textDecoder = new TextDecoder("utf-8");
    const nullChar = textDecoder.decode(new ArrayBuffer(1));
    const names = [];
    for (let i = 0; i < this.model.ngeom; i++) {
      const name = textDecoder.decode(this.model.names.subarray(this.model.name_geomadr[i])).split(nullChar)[0];
      if (/^(obstacle_|barrier_|gate_|block_)/i.test(name)) names.push(name);
    }
    return names;
  }

  // Keyboard steering: hold Up/Down or W/S for +/- vx, Left/Right or A/D for lateral
  // command, Q/E for yaw. The command is part of the policy obs, so this drives the live
  // robot exactly like the sliders.
  bindCommandKeys(r) {
    if (this.unbindCommandKeys) {
      this.unbindCommandKeys();
      this.unbindCommandKeys = null;
    }
    const c = this.pol.command;
    const held = new Set();
    this.commandHeld = held;
    const keyMap = {
      arrowup: 'forward',
      w: 'forward',
      arrowdown: 'back',
      s: 'back',
      arrowleft: 'left',
      a: 'left',
      arrowright: 'right',
      d: 'right',
      q: 'turnLeft',
      e: 'turnRight',
    };
    const apply = () => {
      c[0] = held.has('forward') ? r.vx[1]   : held.has('back') ? r.vx[0]   : 0;
      c[1] = held.has('left')    ? r.vy[1]   : held.has('right') ? r.vy[0]  : 0;
      c[2] = held.has('turnLeft') ? r.vyaw[1] : held.has('turnRight') ? r.vyaw[0] : 0;
      for (const ctl of this.cmdControllers || []) { ctl.updateDisplay(); }
      this.dispatchControlChange();
    };
    // Ignore keystrokes while a GUI text field has focus, so typing a value isn't hijacked.
    const typing = (e) => e.target && /^(INPUT|TEXTAREA)$/.test(e.target.tagName);
    const onKeyDown = (e) => {
      const k = e.key.toLowerCase();
      const command = keyMap[k];
      if (!command || typing(e)) { return; }
      this.lastCommandInputSource = 'keyboard';
      held.add(command); apply(); e.preventDefault();
    };
    const onKeyUp = (e) => {
      const k = e.key.toLowerCase();
      const command = keyMap[k];
      if (!command) { return; }
      held.delete(command); apply(); e.preventDefault();
      if (held.size === 0) {
        this.lastCommandInputSource = 'released';
        this.dispatchControlChange();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    this.unbindCommandKeys = () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
      held.clear();
      this.lastCommandInputSource = 'initial';
    };
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

  async runPolicyLoop(runId = this.policyRunId || 0) {
    const p = this.pol, nsub = p.n_substeps;
    while (this.params.policyRunning && runId === (this.policyRunId || 0)) {
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
    this.updateTelemetryPanel(f);
    this.updateComparePanel(f);
    this.render(0);
    return { frame: f, nframes: this.replayN, nq: this.model.nq, telemetry: this.telemetrySummary(f) };
  }

  compareSummary(frame) {
    if (!this.compare || !this.replayQpos) return null;
    const rolloutFrame = Math.max(0, Math.min(this.replayN - 1, frame));
    const refFrame = Math.max(0, Math.min(this.compare.qpos.length - 1, rolloutFrame));
    const rollout = this.replayQpos[rolloutFrame];
    const reference = this.compare.qpos[refFrame];
    let jointSq = 0;
    let jointCount = 0;
    for (let i = 7; i < Math.min(22, rollout.length, reference.length); i++) {
      const d = rollout[i] - reference[i];
      jointSq += d * d;
      jointCount += 1;
    }
    return {
      frame: rolloutFrame,
      referenceFrame: refFrame,
      frames: Math.min(this.replayN, this.compare.qpos.length),
      rolloutLabel: this.compare.rolloutLabel,
      referenceLabel: this.compare.label,
      rolloutHeight: rollout[2],
      referenceHeight: reference[2],
      heightError: Math.abs(rollout[2] - reference[2]),
      jointRmsError: jointCount ? Math.sqrt(jointSq / jointCount) : 0,
    };
  }

  updateComparePanel(frame) {
    if (!this.compareEls || !this.compare) return;
    const summary = this.compareSummary(frame);
    if (!summary) return;
    this.compareEls.frame.textContent = `frame ${summary.frame}/${this.replayN - 1}`;
    this.compareEls.height.textContent = `height err ${summary.heightError.toFixed(3)}m`;
    this.compareEls.joints.textContent = `joint RMS ${summary.jointRmsError.toFixed(3)}rad`;
    this.compareEls.labels.textContent = `${summary.referenceLabel} vs ${summary.rolloutLabel}`;
  }

  qaCompare(fracs = [0, 0.25, 0.5, 0.75, 1]) {
    if (!this.compare || !this.replayQpos) return { error: 'no compare trajectory' };
    const samples = fracs.map((frac) => {
      const f = Math.max(0, Math.min(this.replayN - 1, Math.round(frac * (this.replayN - 1))));
      return this.compareSummary(f);
    });
    const maxHeightError = samples.reduce((m, s) => Math.max(m, s.heightError), 0);
    const maxJointRmsError = samples.reduce((m, s) => Math.max(m, s.jointRmsError), 0);
    return {
      frames: Math.min(this.replayN, this.compare.qpos.length),
      nq: this.model.nq,
      samples,
      maxHeightError,
      maxJointRmsError,
      pass: maxHeightError <= 0.20 && maxJointRmsError <= 0.35,
    };
  }

  telemetrySummary(frame) {
    if (this.streamFrame) {
      const t = this.streamFrame.telemetry || {};
      const jointVel = Array.isArray(t.joint_vel) ? t.joint_vel : [];
      const maxAbsJointVel = jointVel.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
      return {
        format: this.streamFrame.format || 'physical-ai-stream-frame-v0',
        frame: this.streamFrame.frame ?? this.streamStats.received,
        tick: t.tick ?? this.streamFrame.tick,
        t: t.t ?? this.streamFrame.t,
        joint_count: t.joint_count ?? this.telemetry?.joint_count,
        height: this.data?.qpos ? this.data.qpos[2] : null,
        max_abs_joint_vel: maxAbsJointVel,
        stream: true,
      };
    }
    if (!this.telemetry || !this.telemetry.frames) return null;
    const t = this.telemetry.frames[frame];
    if (!t) return null;
    const jointVel = Array.isArray(t.joint_vel) ? t.joint_vel : [];
    const maxAbsJointVel = jointVel.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
    return {
      format: this.telemetry.format,
      frame,
      tick: t.tick,
      t: t.t,
      joint_count: this.telemetry.joint_count,
      height: this.data?.qpos ? this.data.qpos[2] : null,
      max_abs_joint_vel: maxAbsJointVel,
    };
  }

  updateTelemetryPanel(frame) {
    if (!this.telemetryEls || (!this.telemetry && !this.streamStats?.enabled)) return;
    const summary = this.telemetrySummary(frame);
    if (!summary) return;
    this.telemetryEls.frame.textContent = summary.stream ? `stream ${summary.frame}` : `frame ${summary.frame}/${this.replayN - 1}`;
    this.telemetryEls.tick.textContent = `tick ${summary.tick}`;
    this.telemetryEls.height.textContent = `height ${summary.height?.toFixed(3)}m`;
    this.telemetryEls.jointVel.textContent = `max |dq| ${summary.max_abs_joint_vel.toFixed(2)}`;
  }

  initTelemetryStream(streamUrl) {
    this.streamStats.enabled = true;
    this.params.replay = false;
    if (this.replayToggle) { this.replayToggle.updateDisplay(); }
    try {
      this.streamSocket = new WebSocket(streamUrl);
    } catch (error) {
      console.error('telemetry stream init failed', error);
      this.streamStats.errors += 1;
      return;
    }
    this.streamSocket.addEventListener('open', () => { this.streamStats.connected = true; });
    this.streamSocket.addEventListener('close', () => { this.streamStats.connected = false; });
    this.streamSocket.addEventListener('error', () => { this.streamStats.errors += 1; });
    this.streamSocket.addEventListener('message', (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.format === 'physical-ai-stream-hello-v0') {
          this.streamStats.expectedFrames = message.frames;
          return;
        }
        this.applyStreamFrame(message);
      } catch (error) {
        console.error('telemetry stream frame failed', error);
        this.streamStats.errors += 1;
      }
    });
  }

  applyStreamFrame(frame) {
    if (!frame || !Array.isArray(frame.qpos) || frame.qpos.length !== this.model.nq) {
      throw new Error(`stream qpos must have nq=${this.model.nq}`);
    }
    for (let i = 0; i < this.model.nq; i++) {
      const value = Number(frame.qpos[i]);
      if (!Number.isFinite(value)) { throw new Error(`stream qpos[${i}] is not finite`); }
      this.data.qpos[i] = value;
    }
    this.mujoco.mj_forward(this.model, this.data);
    this.streamFrame = frame;
    const nowMS = performance.now();
    if (this.streamStats.firstReceiveMS === null) { this.streamStats.firstReceiveMS = nowMS; }
    this.streamStats.lastReceiveMS = nowMS;
    this.streamStats.received += 1;
    const tick = frame.telemetry?.tick ?? frame.tick ?? null;
    if (tick !== null && this.streamStats.lastTick !== null && tick < this.streamStats.lastTick) {
      this.streamStats.droppedOrOutOfOrder += 1;
    }
    if (tick !== null && this.streamStats.lastTick !== null && tick === this.streamStats.lastTick) {
      this.streamStats.repeatedTicks += 1;
    }
    this.streamStats.lastTick = tick;
    const height = this.data.qpos[2];
    this.streamStats.minHeight = this.streamStats.minHeight === null ? height : Math.min(this.streamStats.minHeight, height);
    this.streamStats.maxHeight = this.streamStats.maxHeight === null ? height : Math.max(this.streamStats.maxHeight, height);
    this.updateTelemetryPanel(frame.frame ?? this.streamStats.received - 1);
  }

  qaStreamStatus() {
    const elapsedS = this.streamStats.firstReceiveMS !== null && this.streamStats.lastReceiveMS !== null
      ? Math.max(0, (this.streamStats.lastReceiveMS - this.streamStats.firstReceiveMS) / 1000)
      : 0;
    return {
      ...this.streamStats,
      measuredFps: elapsedS > 0 ? Math.max(0, (this.streamStats.received - 1) / elapsedS) : 0,
      heightRange: this.streamStats.minHeight !== null && this.streamStats.maxHeight !== null
        ? this.streamStats.maxHeight - this.streamStats.minHeight
        : null,
      height: this.data?.qpos ? this.data.qpos[2] : null,
      telemetry: this.telemetrySummary(this.streamFrame?.frame ?? 0),
    };
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
    } else if (this.streamStats?.enabled) {
      this.mujoco.mj_forward(this.model, this.data);
    } else if (this.params["replay"] && this.replayQpos) {
      // Grab-to-take-over: if the user starts dragging a body mid-replay, auto-pause the
      // rollout *in place* and hand off to physics. Hold the current pose (ctrl = current
      // qpos) so the arm doesn't snap to home, and don't reset (unlike the manual toggle).
      const grabbed = this.dragStateManager.physicsObject;
      if (grabbed && grabbed.bodyID) {
        this.params.replay = false;
        this.replayToggle?.updateDisplay?.();
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
        this.updateTelemetryPanel(frame);
        this.updateComparePanel(frame);
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
window.dispatchEvent(new CustomEvent('robotics-lab-ready', { detail: { demo } }));
