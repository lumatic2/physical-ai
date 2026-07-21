import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import {
  ALL_FILTER,
  summarizeOverview,
  taskOptions,
  validateGeneralizationRegistry,
} from "../src/components/generalization-lab/generalizationContract.js";

const registry = JSON.parse(await readFile(new URL("../assets/generalization-lab/registry.json", import.meta.url), "utf8"));
validateGeneralizationRegistry(registry);

const all = summarizeOverview(registry, { suite: ALL_FILTER, task: ALL_FILTER });
assert.deepEqual(
  {
    pairs: all.pairedCells,
    episodes: all.policyEpisodes,
    openvla: all.openvlaSuccesses,
    pi05: all.pi05Successes,
    difference: all.differenceSuccesses,
  },
  { pairs: 60, episodes: 120, openvla: 35, pi05: 58, difference: 23 },
);
assert.deepEqual(
  [all.fixedInterval.lower, all.fixedInterval.upper],
  [0.25, 0.5166666666666667],
);

for (const suite of ["libero_spatial", "libero_object", "libero_goal"]) {
  const summary = summarizeOverview(registry, { suite, task: ALL_FILTER });
  assert.equal(summary.pairedCells, 20);
  assert.equal(taskOptions(registry, suite).length, 4);
}

for (const option of taskOptions(registry)) {
  const summary = summarizeOverview(registry, { suite: ALL_FILTER, task: option.key });
  assert.equal(summary.pairedCells, 5);
  assert.equal(summary.policyEpisodes, 10);
}

assert.throws(
  () => summarizeOverview(registry, { suite: "libero_spatial", task: "libero_goal:task-00" }),
  /must not be zero/,
);
const hiddenExclusion = structuredClone(registry);
hiddenExclusion.execution_contract.excluded_pairs = 1;
assert.throws(() => validateGeneralizationRegistry(hiddenExclusion), /hidden exclusions/);

const componentSource = await readFile(
  new URL("../src/components/generalization-lab/GeneralizationLab.jsx", import.meta.url),
  "utf8",
);
for (const rawDisplay of ["openvlaSuccesses", "pi05Successes", "differenceSuccesses", "pairedCells"]) {
  assert.match(componentSource, new RegExp(rawDisplay));
}
assert.match(componentSource, /excluded/);
assert.match(componentSource, /<table>/);
assert.doesNotMatch(componentSource, /general winner|real robot performance|root cause/i);

console.log("generalization overview gate: PASS (60 pairs, 120 episodes, filters and raw counts)");
