export const DEFAULT_ENVIRONMENT_PRESET = "flat-lab";

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

export function normalizeEnvironmentPresetId(id) {
  return ENVIRONMENT_PRESETS[id] ? id : DEFAULT_ENVIRONMENT_PRESET;
}

export function getEnvironmentPreset(id) {
  return ENVIRONMENT_PRESETS[normalizeEnvironmentPresetId(id)];
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
