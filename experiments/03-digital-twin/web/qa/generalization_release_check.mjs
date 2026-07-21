import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const webRoot = fileURLToPath(new URL("..", import.meta.url));
const verifyDir = fileURLToPath(new URL("../verify/generalization-lab/", import.meta.url));
const baseUrl = (process.env.GENERALIZATION_LAB_BASE_URL || "http://127.0.0.1:8132").replace(/\/$/, "");
const prefix = process.env.GENERALIZATION_LAB_PREFIX || (/127\.0\.0\.1|localhost/.test(baseUrl) ? "local" : "live");
const registryBytes = await readFile(new URL("../assets/generalization-lab/registry.json", import.meta.url));
const registry = JSON.parse(registryBytes.toString("utf8"));
const expectedRegistrySha256 = createHash("sha256").update(registryBytes).digest("hex");

await mkdir(verifyDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const consoleErrors = [];
const failedResponses = [];

function observe(page) {
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));
  page.on("response", (response) => { if (response.status() >= 400) failedResponses.push(`${response.status()} ${response.url()}`); });
}

try {
  const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const desktop = await desktopContext.newPage();
  observe(desktop);
  await desktop.goto(`${baseUrl}/generalization-lab.html`, { waitUntil: "networkidle" });
  await desktop.getByRole("heading", { name: "무엇을, 몇 번, 어떻게 비교했는가" }).waitFor();
  assert.equal(await desktop.getByText("60쌍", { exact: true }).count(), 1);
  assert.equal(await desktop.getByText("35 / 60", { exact: true }).count(), 1);
  assert.equal(await desktop.getByText("58 / 60", { exact: true }).count(), 1);
  assert.equal(await desktop.getByText("+23 / 60", { exact: true }).count(), 1);
  assert.equal(await desktop.getByText("27 failures matched", { exact: true }).count(), 1);
  assert.equal(await desktop.getByText("unknown", { exact: true }).count() > 0, true);
  assert.equal(await desktop.getByText("판정하지 않은 양상 3개", { exact: true }).count(), 1);

  const visibleText = await desktop.locator("body").innerText();
  assert.match(visibleText, /Recorded LIBERO simulator evidence only/);
  assert.doesNotMatch(visibleText, /is the general winner|root cause is|live inference is running|performs on a real robot/i);

  await desktop.getByRole("button", { name: "Spatial", exact: true }).click();
  const matrixTask = desktop.locator(".gl-matrix-section select");
  await matrixTask.selectOption("libero_spatial:task-05");
  assert.equal(await desktop.getByText("5쌍", { exact: true }).count(), 1);
  await desktop.getByRole("button", { name: "Spatial · T05 state 00", exact: true }).click();
  const drilldown = desktop.getByRole("link", { name: "이 OpenVLA episode를 듀얼 카메라로 보기", exact: true });
  const drilldownHref = await drilldown.getAttribute("href");
  assert.equal(drilldownHref, registry.cells.find((cell) => cell.cell_id === "libero_spatial:task-05:state-00").public_episode.public_url);

  await desktop.screenshot({ path: `${verifyDir}/${prefix}-desktop-dark.png`, fullPage: true });
  await desktop.getByRole("button", { name: "라이트 모드", exact: true }).click();
  await desktop.screenshot({ path: `${verifyDir}/${prefix}-desktop-light.png`, fullPage: true });

  const replay = await desktopContext.newPage();
  observe(replay);
  await replay.goto(new URL(drilldownHref, `${baseUrl}/`).href, { waitUntil: "networkidle" });
  await replay.waitForFunction(() => window.qaArmLabSummary?.().pass === true && window.qaArmLabSummary().drilldown);
  const replaySummary = await replay.evaluate(() => window.qaArmLabSummary());
  assert.equal(replaySummary.drilldown.sourceCellId, "libero_spatial:task-05:state-00");
  assert.equal(replaySummary.drilldown.manifestSha256, "1197f1e4afbb527d7cbc0f4b924cc4cc4f7b15970f54ace175186b83b9585a47");
  await desktopContext.close();

  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mobile = await mobileContext.newPage();
  observe(mobile);
  await mobile.goto(`${baseUrl}/generalization-lab.html`, { waitUntil: "networkidle" });
  await mobile.getByRole("heading", { name: "무엇을, 몇 번, 어떻게 비교했는가" }).waitFor();
  const horizontalOverflow = await mobile.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert(horizontalOverflow <= 0, { horizontalOverflow });
  assert.equal(await mobile.locator(".gl-failure-filters select").count(), 4);
  await mobile.screenshot({ path: `${verifyDir}/${prefix}-mobile-dark.png`, fullPage: true });
  await mobileContext.close();

  const registryResponse = await fetch(`${baseUrl}/assets/generalization-lab/registry.json`);
  assert.equal(registryResponse.status, 200);
  const servedRegistryBytes = Buffer.from(await registryResponse.arrayBuffer());
  const servedRegistrySha256 = createHash("sha256").update(servedRegistryBytes).digest("hex");
  assert.equal(servedRegistrySha256, expectedRegistrySha256);
  assert.deepEqual(consoleErrors, []);
  assert.deepEqual(failedResponses, []);

  const report = {
    schema_version: "physical-ai-gen5-release-check-v1",
    base_url: baseUrl,
    prefix,
    registry_sha256: servedRegistrySha256,
    denominator: { paired_cells: 60, policy_episodes: 120, failures: 27, unknown: 21 },
    overview: { openvla_successes: 35, pi05_successes: 58, paired_difference: 23 },
    drilldown: { source_cell: replaySummary.drilldown.sourceCellId, manifest_sha256: replaySummary.drilldown.manifestSha256 },
    mobile: { viewport: "390x844", horizontal_overflow: horizontalOverflow, failure_filters: 4 },
    console_errors: consoleErrors,
    failed_responses: failedResponses,
    pass: true,
  };
  await writeFile(`${verifyDir}/${prefix}-release-report.json`, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(`generalization release gate: PASS (${prefix}, 60 pairs, 27 failures, registry ${servedRegistrySha256.slice(0, 12)})`);
} finally {
  await browser.close();
}
