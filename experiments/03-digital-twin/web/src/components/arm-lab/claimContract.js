const ALLOWED_SOURCES = new Set(["sensor", "vlm", "vla", "controller", "environment"]);
const FORBIDDEN_KEYS = new Set(["thought", "thoughts", "reasoning", "rationale", "chain_of_thought", "hidden_reasoning"]);

function rejectHiddenReasoning(value, path = "root") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => rejectHiddenReasoning(item, `${path}[${index}]`));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(key.toLowerCase())) throw new Error(`hidden reasoning field forbidden: ${path}.${key}`);
    rejectHiddenReasoning(child, `${path}.${key}`);
  }
}

export function validatePublicEvidence(registry, eventDocument) {
  const claim = String(registry?.claim_boundary || "").toLowerCase();
  if (!claim.includes("recorded") || !claim.includes("simulation") || !claim.includes("not live") || !claim.includes("real robot")) {
    throw new Error("recorded simulation claim boundary missing");
  }
  if (registry?.camera_contract?.model_input !== "observation.images.image") throw new Error("main model-input camera relabelled");
  if (JSON.stringify(registry?.camera_contract?.observer_only) !== JSON.stringify(["observation.images.image2"])) {
    throw new Error("observer-only camera relabelled");
  }
  const events = eventDocument?.events || [];
  const ids = new Set(events.map((event) => event.id));
  for (const event of events) {
    if (!ALLOWED_SOURCES.has(event.source)) throw new Error(`unsupported event source: ${event.source}`);
    for (const parent of event.parents || []) {
      if (!ids.has(parent)) throw new Error(`broken parent: ${parent}`);
    }
    rejectHiddenReasoning(event.payload);
  }
  if (eventDocument?.lane === "direct_vla" && events.some((event) => event.assistance?.used)) {
    throw new Error("direct VLA assistance relabelled");
  }
  if (eventDocument?.lane === "vlm_skill") {
    const controller = events.find((event) => event.source === "controller");
    if (!controller?.assistance?.used || controller.assistance.source !== "scripted_skill") {
      throw new Error("VLM skill controller assistance missing");
    }
  }
  return { valid: true, lane: eventDocument?.lane, eventCount: events.length };
}
