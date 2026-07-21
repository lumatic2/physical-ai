export const ALL_FILTER = "all";

export const SUITE_LABELS = {
  libero_spatial: "Spatial",
  libero_object: "Object",
  libero_goal: "Goal",
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function validateGeneralizationRegistry(registry) {
  assert(registry?.schema_version === "physical-ai-public-generalization-lab-v1", "registry version mismatch");
  assert(registry?.denominator?.paired_cells === 60, "paired denominator must be 60");
  assert(registry?.denominator?.policy_episodes === 120, "episode denominator must be 120");
  assert(registry?.cells?.length === 60, "registry must contain 60 cells");
  assert(registry?.execution_contract?.planned_pairs === 60, "planned denominator missing");
  assert(registry?.execution_contract?.included_pairs === 60, "included denominator missing");
  assert(registry?.execution_contract?.excluded_pairs === 0, "hidden exclusions are not allowed");
  assert(registry?.execution_contract?.unmatched_pairs === 0, "unmatched pairs are not allowed");
  assert(registry?.failure_summary?.counts?.unknown === 21, "unknown failures must remain visible");
  return registry;
}

export function taskFilterKey(cell) {
  return `${cell.suite}:task-${String(cell.task_id).padStart(2, "0")}`;
}

export function taskOptions(registry, suite = ALL_FILTER) {
  const unique = new Map();
  for (const cell of registry.cells) {
    if (suite !== ALL_FILTER && cell.suite !== suite) continue;
    const key = taskFilterKey(cell);
    if (!unique.has(key)) {
      unique.set(key, {
        key,
        suite: cell.suite,
        taskId: cell.task_id,
        label: `${SUITE_LABELS[cell.suite]} · Task ${String(cell.task_id).padStart(2, "0")}`,
      });
    }
  }
  return [...unique.values()].sort((a, b) => a.key.localeCompare(b.key));
}

export function summarizeOverview(registry, filters = {}) {
  validateGeneralizationRegistry(registry);
  const suite = filters.suite || ALL_FILTER;
  const task = filters.task || ALL_FILTER;
  const cells = registry.cells.filter((cell) => {
    if (suite !== ALL_FILTER && cell.suite !== suite) return false;
    if (task !== ALL_FILTER && taskFilterKey(cell) !== task) return false;
    return true;
  });
  assert(cells.length > 0, "filtered denominator must not be zero");
  const openvlaSuccesses = cells.filter((cell) => cell.policies.openvla.outcome === "success").length;
  const pi05Successes = cells.filter((cell) => cell.policies.pi05.outcome === "success").length;
  return {
    filters: { suite, task },
    cells,
    pairedCells: cells.length,
    policyEpisodes: cells.length * 2,
    openvlaSuccesses,
    pi05Successes,
    differenceSuccesses: pi05Successes - openvlaSuccesses,
    fixedInterval: registry.paired_summary.bootstrap_95,
    executionContract: registry.execution_contract,
  };
}

export function compactHash(value) {
  return value ? `${value.slice(0, 8)}…${value.slice(-6)}` : "—";
}
