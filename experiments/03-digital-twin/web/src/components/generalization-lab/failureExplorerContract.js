import { ALL_FILTER, SUITE_LABELS, taskFilterKey } from "./generalizationContract.js";

export const POLICY_LABELS = {
  "openvla-libero": "OpenVLA",
  "pi05-libero": "π0.5-LIBERO",
};

export const PATTERN_LABELS = {
  no_progress: "no progress",
  unknown: "unknown",
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function collectFailureEpisodes(registry) {
  const failures = [];
  for (const cell of registry.cells) {
    for (const policy of Object.values(cell.policies)) {
      if (policy.outcome === "success") continue;
      assert(policy.outcome === "timeout", "failure explorer only accepts declared timeout outcomes");
      assert(policy.failure?.pattern_id, "failure row is missing an observable pattern");
      assert(policy.failure?.predicates?.length > 0, "failure row is missing observable predicates");
      failures.push({
        cellId: cell.cell_id,
        suite: cell.suite,
        taskId: cell.task_id,
        stateIndex: cell.state_index,
        taskKey: taskFilterKey(cell),
        instruction: cell.instruction,
        policyId: policy.policy_id,
        outcome: policy.outcome,
        manifestSha256: policy.manifest_sha256,
        patternId: policy.failure.pattern_id,
        predicates: policy.failure.predicates,
        frameRange: policy.failure.frame_range,
        ruleVersion: policy.failure.rule_version,
        publicEpisode: policy.public_episode || null,
      });
    }
  }
  failures.sort((a, b) => (
    a.patternId.localeCompare(b.patternId)
    || a.policyId.localeCompare(b.policyId)
    || a.cellId.localeCompare(b.cellId)
  ));
  assert(failures.length === registry.failure_summary.denominator, "failure denominator drift");
  const counts = Object.groupBy(failures, (row) => row.patternId);
  for (const [patternId, expected] of Object.entries(registry.failure_summary.counts)) {
    assert((counts[patternId] || []).length === expected, `${patternId} count drift`);
  }
  assert((counts.unknown || []).length > 0, "unknown failures must not be hidden");
  return failures;
}

export function failureTaskOptions(registry, suite = ALL_FILTER) {
  const unique = new Map();
  for (const row of collectFailureEpisodes(registry)) {
    if (suite !== ALL_FILTER && row.suite !== suite) continue;
    if (!unique.has(row.taskKey)) {
      unique.set(row.taskKey, {
        key: row.taskKey,
        label: `${SUITE_LABELS[row.suite]} · Task ${String(row.taskId).padStart(2, "0")}`,
      });
    }
  }
  return [...unique.values()].sort((a, b) => a.key.localeCompare(b.key));
}

export function filterFailureEpisodes(registry, filters = {}) {
  const policy = filters.policy || ALL_FILTER;
  const suite = filters.suite || ALL_FILTER;
  const task = filters.task || ALL_FILTER;
  const pattern = filters.pattern || ALL_FILTER;
  const rows = collectFailureEpisodes(registry).filter((row) => {
    if (policy !== ALL_FILTER && row.policyId !== policy) return false;
    if (suite !== ALL_FILTER && row.suite !== suite) return false;
    if (task !== ALL_FILTER && row.taskKey !== task) return false;
    if (pattern !== ALL_FILTER && row.patternId !== pattern) return false;
    return true;
  });
  return { filters: { policy, suite, task, pattern }, rows, count: rows.length };
}

export function representativeFailures(rows, limit = 12) {
  if (rows.length <= limit) return rows;
  const selected = [];
  const selectedIds = new Set();
  const strata = new Set();
  for (const row of rows) {
    const stratum = `${row.policyId}:${row.suite}:${row.patternId}`;
    if (strata.has(stratum)) continue;
    strata.add(stratum);
    selected.push(row);
    selectedIds.add(`${row.policyId}:${row.cellId}`);
    if (selected.length === limit) return selected;
  }
  for (const row of rows) {
    const id = `${row.policyId}:${row.cellId}`;
    if (selectedIds.has(id)) continue;
    selected.push(row);
    if (selected.length === limit) break;
  }
  return selected;
}

export function formatPredicate(predicate) {
  const operator = { lt: "<", lte: "≤", eq: "=" }[predicate.operator] || predicate.operator;
  const unit = predicate.unit === "meter" ? " m" : predicate.unit === "count" ? "" : ` ${predicate.unit}`;
  const observed = Number.isInteger(predicate.observed) ? predicate.observed : Number(predicate.observed).toFixed(4);
  return `${predicate.metric} ${observed}${unit} ${operator} ${predicate.threshold}${unit}`;
}
