import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";

import {
  buildDrilldownUrl,
  resolveDrilldown,
} from "../src/components/generalization-lab/drilldownContract.js";

const baseUrl = process.env.GENERALIZATION_LAB_URL || "http://127.0.0.1:8132";
const generalization = JSON.parse(await readFile(new URL("../assets/generalization-lab/registry.json", import.meta.url), "utf8"));
const arm = JSON.parse(await readFile(new URL("../assets/arm-lab/registry.json", import.meta.url), "utf8"));
const linkedCells = generalization.cells.filter((cell) => cell.public_episode);
assert.equal(linkedCells.length, 2);

for (const cell of linkedCells) {
  const url = buildDrilldownUrl(cell);
  assert.equal(url, cell.public_episode.public_url);
  const resolved = resolveDrilldown(url.split("?")[1], generalization, arm);
  assert.equal(resolved.sourceCellId, cell.cell_id);
  assert.equal(resolved.policyId, "openvla-libero");
  assert.equal(resolved.manifestSha256, cell.public_episode.manifest_sha256);
  assert.deepEqual(resolved.cameraSha256, cell.public_episode.camera_sha256);
}

const passCell = linkedCells.find((cell) => cell.public_episode.episode_key === "pass");
const failCell = linkedCells.find((cell) => cell.public_episode.episode_key === "fail");
function mutate(url, key, value) {
  const parsed = new URL(url, "https://example.invalid");
  parsed.searchParams.set(key, value);
  return parsed.search;
}
assert.throws(() => resolveDrilldown(mutate(passCell.public_episode.public_url, "episode", "fail"), generalization, arm), /wrong public episode/);
assert.throws(() => resolveDrilldown(mutate(passCell.public_episode.public_url, "manifest", "0".repeat(64)), generalization, arm), /stale public manifest/);
assert.throws(() => resolveDrilldown(mutate(passCell.public_episode.public_url, "policy", "pi05-libero"), generalization, arm), /policy relabel/);
const relabeledArm = structuredClone(arm);
relabeledArm.episodes.pass.cameras.main.sha256 = "0".repeat(64);
assert.throws(() => resolveDrilldown(new URL(passCell.public_episode.public_url, "https://example.invalid").search, generalization, relabeledArm), /main camera hash relabel/);

const browser = await chromium.launch({ headless: true });
try {
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));

  for (const cell of [passCell, failCell]) {
    await page.goto(new URL(cell.public_episode.public_url, baseUrl).href, { waitUntil: "networkidle" });
    await page.waitForFunction(() => window.qaArmLabSummary?.().pass === true && window.qaArmLabSummary().drilldown);
    const summary = await page.evaluate(() => window.qaArmLabSummary());
    assert.equal(summary.episode, cell.public_episode.episode_key);
    assert.equal(summary.drilldown.sourceCellId, cell.cell_id);
    assert.equal(summary.drilldown.policyId, "openvla-libero");
    assert.equal(summary.drilldown.manifestSha256, cell.public_episode.manifest_sha256);
    assert.equal(summary.drilldown.datasetTreeSha256, cell.public_episode.canonical_dataset_tree_sha256);
    assert.deepEqual(summary.drilldown.cameraSha256, cell.public_episode.camera_sha256);
    await page.getByText(cell.cell_id, { exact: true }).waitFor();
  }

  const staleSearch = mutate(passCell.public_episode.public_url, "manifest", "0".repeat(64));
  await page.goto(new URL(`/arm-lab.html${staleSearch}`, baseUrl).href, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "실험 기록을 열 수 없습니다" }).waitFor();
  assert.match(await page.locator(".arm-state-page p").innerText(), /stale public manifest hash/);
  assert.deepEqual(consoleErrors, []);
} finally {
  await browser.close();
}

console.log("generalization drilldown gate: PASS (2 source-bound LAB3 episodes; negative relabel probes rejected)");
