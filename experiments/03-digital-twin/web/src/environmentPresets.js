export const DEFAULT_ENVIRONMENT_PRESET = "flat-lab";

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

export function summarizeEnvironmentPreset(id, context = {}) {
  const preset = getEnvironmentPreset(id);
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
    groundingMode: context.groundingMode || preset.grounding.defaultMode,
    grounding: preset.grounding,
    physicsProfile: preset.physicsProfile,
    changedRuntime: Boolean(preset.physicsProfile.runtimeChanges),
  };
}
