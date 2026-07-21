import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import { ALL_FILTER } from "../src/components/generalization-lab/generalizationContract.js";
import {
  collectFailureEpisodes,
  filterFailureEpisodes,
  representativeFailures,
} from "../src/components/generalization-lab/failureExplorerContract.js";

const registry = JSON.parse(await readFile(new URL("../assets/generalization-lab/registry.json", import.meta.url), "utf8"));
const all = collectFailureEpisodes(registry);
assert.equal(all.length, 27);
assert.equal(all.filter((row) => row.patternId === "no_progress").length, 6);
assert.equal(all.filter((row) => row.patternId === "unknown").length, 21);
assert.equal(all.filter((row) => row.policyId === "openvla-libero").length, 25);
assert.equal(all.filter((row) => row.policyId === "pi05-libero").length, 2);
assert.deepEqual(
  Object.fromEntries(["libero_goal", "libero_object", "libero_spatial"].map((suite) => [suite, filterFailureEpisodes(registry, { suite }).count])),
  { libero_goal: 12, libero_object: 8, libero_spatial: 7 },
);

const sample = representativeFailures(all);
assert.equal(sample.length, 12);
assert(sample.every((row) => row.outcome === "timeout"), "success-only or success-contaminated sampling is forbidden");
assert(sample.some((row) => row.patternId === "unknown"), "unknown must remain in the representative sample");
assert(sample.some((row) => row.patternId === "no_progress"));
assert(sample.some((row) => row.policyId === "pi05-libero"));

const noProgress = filterFailureEpisodes(registry, { pattern: "no_progress" });
assert.equal(noProgress.count, 6);
assert(noProgress.rows.every((row) => row.predicates[0].metric === "end_effector_displacement"));
assert.equal(filterFailureEpisodes(registry, { policy: "pi05-libero", pattern: "unknown" }).count, 1);
assert.equal(filterFailureEpisodes(registry, { policy: "pi05-libero", pattern: "no_progress" }).count, 1);
assert.equal(filterFailureEpisodes(registry, { suite: "libero_spatial", task: "libero_spatial:task-00" }).count, 0);

const hiddenUnknown = structuredClone(registry);
hiddenUnknown.failure_summary.counts.unknown = 0;
assert.throws(() => collectFailureEpisodes(hiddenUnknown), /unknown count drift/);

const componentSource = await readFile(new URL("../src/components/generalization-lab/FailureExplorer.jsx", import.meta.url), "utf8");
assert.match(componentSource, /unknown/);
assert.match(componentSource, /predicates\[0\]/);
assert.match(componentSource, /숨은 원인을 진단하지 않습니다/);
assert.doesNotMatch(componentSource, /원인은|caused by|root cause:|failed because/i);
assert.doesNotMatch(componentSource, /outcome === ["']success["']/);
assert.match(componentSource, /disabled_patterns/);
assert.equal(filterFailureEpisodes(registry, { policy: ALL_FILTER }).count, 27);

console.log("generalization failure explorer gate: PASS (27 failures, no_progress=6, unknown=21)");
