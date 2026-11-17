import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, createClient, optimizationPayload, resolveBase, scenarioPayload, validateFloodTile } from '../src/api.js';

test('API base defaults to same-origin /api and rejects unsafe URLs', () => {
  assert.equal(resolveBase(''), '/api');
  assert.equal(resolveBase('https://safarsaathi.onrender.com/'), 'https://safarsaathi.onrender.com');
  assert.throws(() => resolveBase('https://user:pw@example.com'));
  assert.throws(() => resolveBase('ftp://example.com'));
});

test('scenario payload mirrors backend bounds', () => {
  assert.deepEqual(scenarioPayload({ baseline_visitors: '100', capacity: 120, demand_change_percent: '50', available_capacity_percent: 50 }),
    { baseline_visitors: 100, capacity: 120, demand_change_percent: 50, available_capacity_percent: 50 });
  assert.throws(() => scenarioPayload({ baseline_visitors: 1, capacity: 0, demand_change_percent: 0, available_capacity_percent: 50 }), /Capacity/);
  assert.throws(() => scenarioPayload({ baseline_visitors: '', capacity: 1, demand_change_percent: 0, available_capacity_percent: 50 }), /Baseline/);
});

test('optimization payload validates rows, ids and solver settings', () => {
  const base = { demand: 10, exposure_tradeoff: 0.5, algorithm: 'ga', seed: 1, population: 16, iterations: 10,
    destinations: [{ id: 'A', capacity: 10, accessibility: 1, road_capacity: 10, resource_capacity: 10, exposure_weight: 0.3 }] };
  assert.equal(optimizationPayload(base).problem.destinations[0].id, 'A');
  assert.throws(() => optimizationPayload({ ...base, destinations: [...base.destinations, base.destinations[0]] }), /unique/);
  assert.throws(() => optimizationPayload({ ...base, population: 4 }), /Population/);
  assert.throws(() => optimizationPayload({ ...base, iterations: 2.5 }), /whole number/);
  assert.throws(() => optimizationPayload({ ...base, algorithm: 'sa' }), /GA or PSO/);
});

test('flood tile validation checks shape and metadata', () => {
  const image = Array.from({ length: 128 }, () => Array.from({ length: 128 }, () => [0.1, -0.2]));
  assert.ok(validateFloodTile({ image, metadata: { source_format: 'STURM-S1-preprocessed', geo_tags: {} } }));
  assert.throws(() => validateFloodTile({ image: image.slice(1), metadata: { source_format: 'STURM-S1-preprocessed' } }), /128/);
  assert.throws(() => validateFloodTile({ image, metadata: { source_format: 'raw' } }), /source_format/);
});

test('client classifies HTTP failures and network errors', async () => {
  const reply = (status, body) => async () => ({ ok: status < 400, status, json: async () => body });
  await assert.rejects(createClient('/api', 1000, reply(503, { detail: 'no data' }))('/x'), e => e instanceof ApiError && e.kind === 'unavailable' && e.message === 'no data');
  await assert.rejects(createClient('/api', 1000, reply(422, { detail: 'bad' }))('/x'), e => e.kind === 'invalid');
  await assert.rejects(createClient('/api', 1000, async () => { throw new TypeError('fail'); })('/x'), e => e.kind === 'network');
  assert.deepEqual(await createClient('/api', 1000, reply(200, { ok: 1 }))('/x'), { ok: 1 });
});

const live = process.env.SAFARSAATHI_TEST_API;
test('every public route answers against a running backend', { skip: !live }, async () => {
  const request = createClient(live);
  for (const path of ['/health', '/models', '/capabilities', '/destinations', '/destinations/kedarnath/climate', '/tourism/history', '/optimization/metadata', '/deployment/status']) {
    assert.ok(await request(path), path);
  }
  const r = await request('/scenarios/simulate', { method: 'POST', body: { baseline_visitors: 100, capacity: 120, demand_change_percent: 50, available_capacity_percent: 50 } });
  assert.equal(r.scenario.unserved_visitors, 90);
});
