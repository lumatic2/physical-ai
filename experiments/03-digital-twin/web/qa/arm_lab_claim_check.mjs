import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { validatePublicEvidence } from '../src/components/arm-lab/claimContract.js';

const WEB_ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const BUNDLE = join(WEB_ROOT, 'assets', 'arm-lab');
const load = (path) => JSON.parse(readFileSync(join(BUNDLE, path), 'utf8'));
const registry = load('registry.json');

for (const [outcome, episode] of Object.entries(registry.episodes)) {
  for (const [lane, artifact] of Object.entries(episode.event_lanes)) {
    const document = load(artifact.path);
    const result = validatePublicEvidence(registry, document);
    assert.equal(result.valid, true);
    assert.equal(result.lane, lane);
    assert.ok(result.eventCount > 0);

    const hidden = structuredClone(document);
    hidden.events[0].payload.reasoning = 'private scratchpad';
    assert.throws(() => validatePublicEvidence(registry, hidden), /hidden reasoning/);

    const unknown = structuredClone(document);
    unknown.events[0].source = 'oracle';
    assert.throws(() => validatePublicEvidence(registry, unknown), /unsupported event source/);
    console.log(`[claim] ${outcome}/${lane} PASS (${result.eventCount} events)`);
  }
}

const liveRelabel = structuredClone(registry);
liveRelabel.claim_boundary = 'live real robot telemetry';
assert.throws(() => validatePublicEvidence(liveRelabel, load(registry.episodes.pass.event_lanes.direct_vla.path)), /claim boundary/);

const cameraRelabel = structuredClone(registry);
cameraRelabel.camera_contract.model_input = 'observation.images.image2';
assert.throws(() => validatePublicEvidence(cameraRelabel, load(registry.episodes.pass.event_lanes.direct_vla.path)), /camera relabelled/);

console.log('[claim] negative relabel probes PASS');
