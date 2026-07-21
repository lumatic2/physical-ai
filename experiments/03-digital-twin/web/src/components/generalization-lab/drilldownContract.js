import { validateGeneralizationRegistry } from "./generalizationContract.js";

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

export function episodeFromSearch(search) {
  const value = new URLSearchParams(search).get("episode");
  return value === "fail" ? "fail" : "pass";
}

export function hasDrilldownRequest(search) {
  return new URLSearchParams(search).has("source_cell");
}

export function traceablePolicy(cell) {
  if (!cell?.public_episode) return null;
  const policy = Object.values(cell.policies).find((candidate) => candidate.run_key === cell.public_episode.run_key);
  assert(policy, "public episode policy is missing from its source cell");
  assert(policy.manifest_sha256 === cell.public_episode.manifest_sha256, "source manifest drift");
  return policy;
}

export function buildDrilldownUrl(cell) {
  const link = cell?.public_episode;
  const policy = traceablePolicy(cell);
  assert(link && policy, "cell has no public drilldown episode");
  const query = new URLSearchParams();
  query.set("episode", link.episode_key);
  query.set("source_cell", cell.cell_id);
  query.set("policy", policy.policy_id);
  query.set("manifest", link.manifest_sha256);
  return `/arm-lab.html?${query.toString()}`;
}

export function resolveDrilldown(search, generalizationRegistry, armRegistry) {
  validateGeneralizationRegistry(generalizationRegistry);
  assert(armRegistry?.schema_version === "physical-ai-public-arm-lab-v1", "arm registry version mismatch");
  const query = new URLSearchParams(search);
  const episodeKey = query.get("episode");
  const sourceCellId = query.get("source_cell");
  const policyId = query.get("policy");
  const manifestSha256 = query.get("manifest");
  assert([episodeKey, sourceCellId, policyId, manifestSha256].every(Boolean), "drilldown query is incomplete");
  assert(episodeKey === "pass" || episodeKey === "fail", "drilldown episode is invalid");

  const cell = generalizationRegistry.cells.find((candidate) => candidate.cell_id === sourceCellId);
  assert(cell?.public_episode, "source cell has no public episode");
  const link = cell.public_episode;
  const policy = traceablePolicy(cell);
  assert(link.episode_key === episodeKey, "wrong public episode for source cell");
  assert(policy.policy_id === policyId, "public episode policy relabel");
  assert(link.manifest_sha256 === manifestSha256, "stale public manifest hash");

  const armEpisode = armRegistry.episodes?.[episodeKey];
  assert(armEpisode?.id === link.episode_id, "arm episode identity drift");
  assert(armEpisode.instruction === cell.instruction, "arm episode instruction drift");
  assert(armEpisode.canonical_dataset_tree_sha256 === link.canonical_dataset_tree_sha256, "dataset tree hash drift");
  for (const role of ["main", "wrist"]) {
    assert(armEpisode.cameras?.[role]?.sha256 === link.camera_sha256?.[role], `${role} camera hash relabel`);
  }
  const expectedOutcome = episodeKey === "pass" ? "success" : "timeout";
  assert(policy.outcome === expectedOutcome, "source outcome drift");

  return {
    episodeKey,
    episodeId: link.episode_id,
    sourceCellId,
    policyId,
    manifestSha256,
    runKey: link.run_key,
    datasetTreeSha256: link.canonical_dataset_tree_sha256,
    cameraSha256: link.camera_sha256,
    instruction: cell.instruction,
  };
}
