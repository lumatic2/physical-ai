export const DEFAULT_ENVIRONMENT_PRESET = "flat-lab";
export const DEFAULT_ENVIRONMENT_SCENARIO_ID = "flat-lab-v1";

export const GROUNDING_MODES = {
  "replay-locked": {
    id: "replay-locked",
    label: "Replay locked",
    shortLabel: "replay",
    claimLevel: "kinematic-replay",
    behaviorMutation: false,
    evidenceRequired: "qpos trajectory contract; not a free-physics stability proof",
    warning: "Replay sets qpos from recorded frames and must not be described as controller stability.",
  },
  "assisted-fixture": {
    id: "assisted-fixture",
    label: "Assisted fixture",
    shortLabel: "assisted",
    claimLevel: "assisted-sim-fixture",
    behaviorMutation: false,
    evidenceRequired: "support/fixture source plus stability gate; not unassisted success",
    warning: "Assisted fixture evidence must not be presented as unassisted standing or real telemetry.",
  },
  "physics-contact": {
    id: "physics-contact",
    label: "Physics contact",
    shortLabel: "physics",
    claimLevel: "free-contact-check",
    behaviorMutation: false,
    evidenceRequired: "fall/contact/slip metrics under free MuJoCo stepping",
    warning: "Free contact mode needs stability evidence before being called successful.",
  },
  "controller-backed": {
    id: "controller-backed",
    label: "Controller backed",
    shortLabel: "controller",
    claimLevel: "controller-backed-sim",
    behaviorMutation: false,
    evidenceRequired: "policy/LowCmd/controller gate with height/contact stability",
    warning: "Controller-backed means simulated controller evidence unless real telemetry is separately supplied.",
  },
};

const GROUNDING_ALIASES = {
  replay: "replay-locked",
  locked: "replay-locked",
  assisted: "assisted-fixture",
  fixture: "assisted-fixture",
  physics: "physics-contact",
  contact: "physics-contact",
  controller: "controller-backed",
  policy: "controller-backed",
};

export const ENVIRONMENT_PRESETS = {
  "flat-lab": {
    id: "flat-lab",
    label: "Flat lab",
    claimLevel: "visual+contract",
    visual: {
      mood: "calibrated lab",
      background: "cool neutral",
      lighting: "single key plus ambient",
      markers: ["floor grid", "origin axes"],
    },
    scene: {
      mode: "current-experiment-scene",
      reloadRequired: false,
      mutation: "none",
    },
    floor: {
      profile: "flat reference floor",
      terrain: "flat",
      material: "current MJCF material",
    },
    contactProfile: {
      intent: "baseline contact",
      friction: "scene-default",
      condim: "scene-default",
      solver: "scene-default",
    },
    grounding: {
      defaultMode: "replay-locked",
      allowedModes: ["replay-locked", "assisted-fixture", "physics-contact", "controller-backed"],
      assistStrength: "scene-or-trace-default",
    },
    physicsProfile: {
      state: "unchanged",
      knobs: ["groundingMode", "contactProfile"],
      runtimeChanges: false,
    },
  },
  "instrumented-lab": {
    id: "instrumented-lab",
    label: "Instrumented lab",
    claimLevel: "visual+contract",
    visual: {
      mood: "measurement bay",
      background: "dark lab wall",
      lighting: "inspection key plus rim",
      markers: ["floor grid", "origin axes", "height bands", "contact readouts"],
    },
    scene: {
      mode: "current-experiment-scene",
      reloadRequired: false,
      mutation: "none",
    },
    floor: {
      profile: "instrumented flat floor",
      terrain: "flat",
      material: "current MJCF material",
    },
    contactProfile: {
      intent: "measurement-first contact summary",
      friction: "scene-default",
      condim: "scene-default",
      solver: "scene-default",
    },
    grounding: {
      defaultMode: "assisted-fixture",
      allowedModes: ["replay-locked", "assisted-fixture", "physics-contact", "controller-backed"],
      assistStrength: "reported-only",
    },
    physicsProfile: {
      state: "unchanged",
      knobs: ["groundingMode", "assistStrength", "contactFrames"],
      runtimeChanges: false,
    },
  },
  "rough-terrain": {
    id: "rough-terrain",
    label: "Rough terrain",
    claimLevel: "scene-contract-pending",
    visual: {
      mood: "terrain test lane",
      background: "industrial neutral",
      lighting: "high contrast test rig",
      markers: ["floor grid", "curb lane", "terrain boundary"],
    },
    scene: {
      mode: "scene-variant-required",
      reloadRequired: true,
      mutation: "deferred-to-step2",
    },
    floor: {
      profile: "rough/curb terrain",
      terrain: "rough",
      material: "rough MJCF variant",
    },
    contactProfile: {
      intent: "terrain perturbation",
      friction: "variant-defined",
      condim: "variant-defined",
      solver: "variant-defined",
    },
    grounding: {
      defaultMode: "physics-contact",
      allowedModes: ["physics-contact", "controller-backed"],
      assistStrength: "none-by-default",
    },
    physicsProfile: {
      state: "requires-scene-reload",
      knobs: ["terrainVariant", "contactProfile", "groundingMode"],
      runtimeChanges: false,
    },
  },
};

export const ENVIRONMENT_SCENARIOS = {
  "flat-lab-v1": {
    id: "flat-lab-v1",
    label: "Flat lab v1",
    seed: "env-flat-0001",
    preset: "flat-lab",
    terrain: {
      kind: "flat-plane",
      heightM: 0,
      laneLengthM: 4,
    },
    friction: {
      floor: "scene-default",
      curb: null,
      obstacle: null,
    },
    lighting: {
      profile: "neutral-key-ambient",
      intensity: "preset-default",
    },
    obstacle: {
      enabled: false,
      type: "none",
      count: 0,
    },
    parameters: {
      replayStartFrame: 0,
      expectedTerrainGeomMin: 0,
      expectedObstacleGeomMin: 0,
    },
    matrixTags: ["baseline", "flat"],
    claimBoundary: "Flat reference lab contract only; not a terrain robustness proof.",
  },
  "instrumented-lab-v1": {
    id: "instrumented-lab-v1",
    label: "Instrumented lab v1",
    seed: "env-instrumented-0001",
    preset: "instrumented-lab",
    terrain: {
      kind: "flat-measurement-plane",
      heightM: 0,
      laneLengthM: 4,
    },
    friction: {
      floor: "scene-default",
      curb: null,
      obstacle: null,
    },
    lighting: {
      profile: "inspection-key-rim",
      intensity: "measurement-bay",
    },
    obstacle: {
      enabled: false,
      type: "none",
      count: 0,
    },
    parameters: {
      replayStartFrame: 0,
      expectedTerrainGeomMin: 0,
      expectedObstacleGeomMin: 0,
    },
    matrixTags: ["instrumented", "flat"],
    claimBoundary: "Measurement overlay contract only; does not change physics by itself.",
  },
  "rough-curb-v1": {
    id: "rough-curb-v1",
    label: "Rough curb v1",
    seed: "env-rough-curb-0001",
    preset: "rough-terrain",
    terrain: {
      kind: "curb-lane",
      curbHeightsM: [0.01, 0.02, 0.03],
      curbPositionsM: [1.0, 2.0, 3.0],
      laneLengthM: 4,
    },
    friction: {
      floor: 0.65,
      curb: 0.8,
      obstacle: null,
    },
    lighting: {
      profile: "high-contrast-terrain-rig",
      intensity: "terrain-test",
    },
    obstacle: {
      enabled: false,
      type: "none",
      count: 0,
    },
    parameters: {
      replayStartFrame: 0,
      expectedTerrainGeomMin: 3,
      expectedObstacleGeomMin: 0,
    },
    matrixTags: ["rough", "curb", "contact-bearing"],
    claimBoundary: "Curb-lane scenario evidence only; not broad outdoor mobility.",
  },
  "obstacle-lane-v1": {
    id: "obstacle-lane-v1",
    label: "Obstacle lane v1",
    seed: "env-obstacle-lane-0001",
    preset: "rough-terrain",
    terrain: {
      kind: "offset-obstacle-lane",
      curbHeightsM: [0.015, 0.025],
      laneLengthM: 4,
    },
    friction: {
      floor: 0.65,
      curb: 0.8,
      obstacle: 0.85,
    },
    lighting: {
      profile: "high-contrast-obstacle-rig",
      intensity: "terrain-test",
    },
    obstacle: {
      enabled: true,
      type: "offset-box-lane",
      count: 3,
      clearanceM: 0.28,
      heightsM: [0.035, 0.045, 0.04],
    },
    parameters: {
      replayStartFrame: 0,
      expectedTerrainGeomMin: 2,
      expectedObstacleGeomMin: 3,
    },
    matrixTags: ["rough", "obstacle", "contact-bearing"],
    claimBoundary: "Obstacle-lane smoke evidence only; not autonomous obstacle avoidance.",
  },
};

export const EPISODE_RANDOMIZATION_PROFILES = {
  "obstacle-command-noise-v1": {
    id: "obstacle-command-noise-v1",
    label: "Obstacle command/noise v1",
    seed: "episode-obstacle-0001",
    experiment: "g1-obstacle-walk",
    scenario: "obstacle-lane-v1",
    steps: 180,
    chunk: 45,
    axes: {
      command: {
        applied: true,
        description: "Policy velocity command vector per episode.",
      },
      controlNoise: {
        applied: true,
        description: "MuJoCo ctrl noise parameters already exposed by the web runtime.",
      },
      friction: {
        applied: false,
        description: "Recorded in scenario contract; runtime friction randomization needs MJCF variants.",
      },
      sensorNoise: {
        applied: false,
        description: "Recorded as boundary only; observation-noise injection is not implemented in this browser policy path.",
      },
    },
    passCriteria: {
      maxFallHeightM: 0.2,
      minDistanceM: 0.02,
      maxAbsYDriftM: 3.0,
      requireFiniteState: true,
    },
    episodes: [
      {
        id: "seed-0001-forward-clean",
        seed: "episode-obstacle-0001-a",
        command: [0.55, 0.0, 0.0],
        ctrlNoiseStd: 0.0,
        ctrlNoiseRate: 0.0,
      },
      {
        id: "seed-0002-forward-low-noise",
        seed: "episode-obstacle-0001-b",
        command: [0.5, 0.0, 0.08],
        ctrlNoiseStd: 0.015,
        ctrlNoiseRate: 1.0,
      },
      {
        id: "seed-0003-diagonal-low-noise",
        seed: "episode-obstacle-0001-c",
        command: [0.45, 0.18, -0.06],
        ctrlNoiseStd: 0.02,
        ctrlNoiseRate: 1.4,
      },
    ],
    claimBoundary: "Seeded browser episode scorecard for command/control-noise perturbations; not a training-time domain-randomization or sim-to-real proof.",
  },
};

const DEFAULT_SCENARIO_BY_PRESET = {
  "flat-lab": "flat-lab-v1",
  "instrumented-lab": "instrumented-lab-v1",
  "rough-terrain": "rough-curb-v1",
};

export function normalizeEnvironmentPresetId(id) {
  return ENVIRONMENT_PRESETS[id] ? id : DEFAULT_ENVIRONMENT_PRESET;
}

export function getEnvironmentPreset(id) {
  return ENVIRONMENT_PRESETS[normalizeEnvironmentPresetId(id)];
}

export function normalizeEnvironmentScenarioId(id, presetId = null) {
  if (ENVIRONMENT_SCENARIOS[id]) return id;
  const preset = normalizeEnvironmentPresetId(presetId);
  return DEFAULT_SCENARIO_BY_PRESET[preset] || DEFAULT_ENVIRONMENT_SCENARIO_ID;
}

export function getEnvironmentScenario(id, presetId = null) {
  return ENVIRONMENT_SCENARIOS[normalizeEnvironmentScenarioId(id, presetId)];
}

export function normalizeEpisodeRandomizationProfileId(id) {
  return EPISODE_RANDOMIZATION_PROFILES[id] ? id : "obstacle-command-noise-v1";
}

export function getEpisodeRandomizationProfile(id) {
  return EPISODE_RANDOMIZATION_PROFILES[normalizeEpisodeRandomizationProfileId(id)];
}

export function inferEnvironmentScenarioFromExperiment(exp = {}) {
  const scene = exp.scene || "";
  const title = exp.title || "";
  if (/obstacle/i.test(`${scene} ${title}`)) return "obstacle-lane-v1";
  if (/rough|curb/i.test(scene)) return "rough-curb-v1";
  return DEFAULT_ENVIRONMENT_SCENARIO_ID;
}

export function normalizeGroundingMode(id, allowedModes = null, fallback = "replay-locked") {
  const normalized = GROUNDING_ALIASES[id] || id;
  const candidate = GROUNDING_MODES[normalized] ? normalized : fallback;
  if (!allowedModes || allowedModes.includes(candidate)) return candidate;
  return allowedModes.includes(fallback) ? fallback : allowedModes[0];
}

export function inferGroundingModeFromExperiment(exp = {}) {
  const scene = exp.scene || "";
  const title = exp.title || "";
  if (exp.policy) return "controller-backed";
  if (exp.telemetry_sidecar && /elastic|assisted/i.test(`${title} ${exp.trajectory || ""}`)) {
    return "assisted-fixture";
  }
  if (/rough|curb/i.test(scene)) return "physics-contact";
  return "replay-locked";
}

export function inferEnvironmentPresetFromExperiment(exp = {}) {
  return /rough|curb/i.test(exp.scene || "") ? "rough-terrain" : DEFAULT_ENVIRONMENT_PRESET;
}

export function getGroundingMode(id) {
  return GROUNDING_MODES[normalizeGroundingMode(id)];
}

export function summarizeEnvironmentPreset(id, context = {}) {
  const preset = getEnvironmentPreset(id);
  const defaultGrounding = normalizeGroundingMode(
    context.defaultGroundingMode || preset.grounding.defaultMode,
    preset.grounding.allowedModes,
    preset.grounding.defaultMode,
  );
  const requestedGrounding = context.requestedGroundingMode || context.groundingMode || defaultGrounding;
  const groundingMode = normalizeGroundingMode(
    requestedGrounding,
    preset.grounding.allowedModes,
    defaultGrounding,
  );
  const grounding = getGroundingMode(groundingMode);
  return {
    preset: preset.id,
    label: preset.label,
    claimLevel: preset.claimLevel,
    visual: preset.visual,
    scene: {
      ...preset.scene,
      activeScene: context.scene || null,
      contactBearingTerrain: Boolean(context.contactBearingTerrain),
      terrainGeomCount: context.terrainGeomCount || 0,
      terrainGeomNames: context.terrainGeomNames || [],
    },
    floor: preset.floor,
    contactProfile: preset.contactProfile,
    groundingMode,
    grounding: preset.grounding,
    groundingControl: {
      requestedMode: requestedGrounding,
      defaultMode: defaultGrounding,
      appliedMode: groundingMode,
      source: context.requestedGroundingMode ? "user" : "experiment-default",
      allowedModes: preset.grounding.allowedModes,
      behaviorMutation: grounding.behaviorMutation,
      label: grounding.label,
      shortLabel: grounding.shortLabel,
      claimLevel: grounding.claimLevel,
      evidenceRequired: grounding.evidenceRequired,
      warning: grounding.warning,
    },
    physicsProfile: preset.physicsProfile,
    changedRuntime: Boolean(preset.physicsProfile.runtimeChanges || grounding.behaviorMutation),
  };
}

export function summarizeEnvironmentScenario(id, context = {}) {
  const scenario = getEnvironmentScenario(id, context.preset);
  const obstacleGeomCount = context.obstacleGeomCount || 0;
  const terrainGeomCount = context.terrainGeomCount || 0;
  return {
    id: scenario.id,
    label: scenario.label,
    seed: scenario.seed,
    preset: scenario.preset,
    terrain: scenario.terrain,
    friction: scenario.friction,
    lighting: scenario.lighting,
    obstacle: {
      ...scenario.obstacle,
      sceneGeomCount: obstacleGeomCount,
      sceneGeomNames: context.obstacleGeomNames || [],
    },
    parameters: scenario.parameters,
    matrixTags: scenario.matrixTags,
    claimBoundary: scenario.claimBoundary,
    scene: context.scene || null,
    terrainGeomCount,
    terrainGeomNames: context.terrainGeomNames || [],
    contactBearingTerrain: Boolean(context.contactBearingTerrain),
    pass: Boolean(
      scenario.id &&
      scenario.seed &&
      scenario.terrain?.kind &&
      scenario.friction &&
      scenario.lighting?.profile &&
      scenario.obstacle &&
      scenario.claimBoundary &&
      terrainGeomCount >= (scenario.parameters?.expectedTerrainGeomMin || 0) &&
      obstacleGeomCount >= (scenario.parameters?.expectedObstacleGeomMin || 0)
    ),
  };
}

export function summarizeEpisodeRandomizationProfile(id) {
  const profile = getEpisodeRandomizationProfile(id);
  const appliedAxes = Object.entries(profile.axes)
    .filter(([, axis]) => axis.applied)
    .map(([name]) => name);
  const boundaryAxes = Object.entries(profile.axes)
    .filter(([, axis]) => !axis.applied)
    .map(([name]) => name);
  return {
    id: profile.id,
    label: profile.label,
    seed: profile.seed,
    experiment: profile.experiment,
    scenario: profile.scenario,
    steps: profile.steps,
    chunk: profile.chunk,
    episodeCount: profile.episodes.length,
    appliedAxes,
    boundaryAxes,
    axes: profile.axes,
    passCriteria: profile.passCriteria,
    claimBoundary: profile.claimBoundary,
  };
}
