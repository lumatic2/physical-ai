import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(here, '../03-digital-twin/web');
const require = createRequire(path.join(webRoot, 'package.json'));
const { chromium } = require('playwright');
const outPath = path.join(here, 'verify/browser-reference-vs-rollout.json');
const url = process.env.PHYSICAL_AI_WEB_URL || 'http://127.0.0.1:8132/?exp=g1-squat-reference-vs-wbc';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('console', (msg) => {
  if (msg.type() === 'error') errors.push(msg.text());
});
page.on('pageerror', (err) => errors.push(String(err)));

await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForFunction(() => window.demo && typeof window.demo.qaCompare === 'function', null, { timeout: 60000 });
const compare = await page.evaluate(() => window.demo.qaCompare([0, 0.25, 0.5, 0.75, 1]));
const title = await page.locator('.robot-picker__name').textContent().catch(() => null);
const screenshot = path.join(here, 'verify/browser-reference-vs-rollout.png');
await page.screenshot({ path: screenshot, fullPage: false });
await browser.close();

const result = {
  verdict: !compare.error && errors.length === 0 && compare.frames >= 100 ? 'PASS' : 'FAIL',
  url,
  title,
  compare,
  console_errors: errors,
  screenshot: path.relative(path.resolve(here, '../..'), screenshot).replaceAll(path.sep, '/'),
};

await fs.mkdir(path.dirname(outPath), { recursive: true });
await fs.writeFile(outPath, JSON.stringify(result, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(result, null, 2));
process.exit(result.verdict === 'PASS' ? 0 : 1);
