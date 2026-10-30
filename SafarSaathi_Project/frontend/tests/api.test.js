import test from 'node:test';
import assert from 'node:assert/strict';
import { createClient, ApiError, cachedRead } from '../src/services/api/client.js';
import { scenarioPayload, projectLocations, pageCards, number } from '../src/services/api/adapters.js';

async function withFetch(mock, run) {
  const original = globalThis.fetch;
  globalThis.fetch = mock;
  try { await run(); } finally { globalThis.fetch = original; }
}

test('client sends bounded JSON POSTs with no credentials and handles JSON', async () => {
  await withFetch(async (url, init) => {
    assert.equal(url, 'http://localhost:8000/scenarios/simulate');
    assert.equal(init.credentials, 'omit');
    assert.equal(init.method, 'POST');
    assert.equal(init.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(init.body), { example: 1 });
    return new Response('{"status":"ok"}');
  }, async () => assert.deepEqual(await createClient('http://localhost:8000/')('/scenarios/simulate', { method: 'POST', body: { example: 1 } }), { status: 'ok' }));
});

test('HTTP unavailable, validation and invalid JSON responses are explicit errors', async () => {
  for (const status of [422, 501, 503]) await withFetch(async () => new Response('{"detail":"Specific failure"}', { status }), async () => {
    await assert.rejects(createClient()('/models'), e => e instanceof ApiError && e.status === status && e.message === 'Specific failure');
  });
  await withFetch(async () => new Response('<html>bad gateway</html>', { status: 502 }), async () => {
    await assert.rejects(createClient()('/models'), e => e.kind === 'format');
  });
});

test('timeout, network failure and no automatic POST retry', async () => {
  let calls = 0;
  await withFetch(async () => { calls++; throw new TypeError('Connection refused'); }, async () => {
    await assert.rejects(createClient()('/scenarios/simulate', { method: 'POST', body: {} }), e => e.kind === 'network');
  });
  assert.equal(calls, 1);
  await withFetch((url, init) => new Promise((resolve, reject) => init.signal.addEventListener('abort', () => reject(new Error('aborted')))), async () => {
    await assert.rejects(createClient('http://localhost:8000', 5)('/models'), e => e.kind === 'timeout');
  });
});

test('API URL rejects embedded credentials and non-HTTP protocols', () => {
  assert.throws(() => createClient('file:///private'));
  assert.throws(() => createClient('https://user:secret@example.com'));
  assert.throws(() => createClient('https://example.com?token=secret'));
});

test('GET cache deduplicates pending requests and retries failures without fake fallback', async () => {
  let calls = 0;
  const loader = async () => { calls++; return { actual: 3 }; };
  const values = await Promise.all([cachedRead('dedupe-test', loader), cachedRead('dedupe-test', loader)]);
  assert.equal(calls, 1);
  assert.deepEqual(values, [{ actual: 3 }, { actual: 3 }]);
  await cachedRead('dedupe-test', loader);
  assert.equal(calls, 1);
  await cachedRead('dedupe-test', loader, true);
  assert.equal(calls, 2);
  await assert.rejects(cachedRead('failure-test', async () => { throw new Error('offline'); }));
  assert.equal(await cachedRead('failure-test', async () => 4), 4);
});

test('scenario adapter accepts explicit numeric inputs and rejects blank, boolean, invalid bounds', () => {
  const valid = { baseline_visitors: '100', capacity: '120', demand_change_percent: '50', available_capacity_percent: '50' };
  assert.deepEqual(scenarioPayload(valid), { baseline_visitors: 100, capacity: 120, demand_change_percent: 50, available_capacity_percent: 50 });
  for (const value of ['', ' ', null, true, -1, Infinity, NaN]) assert.throws(() => scenarioPayload({ ...valid, capacity: value }));
  assert.throws(() => scenarioPayload({ ...valid, available_capacity_percent: 101 }));
});

test('map adapter preserves longitude/latitude, filters bad coordinates and handles degenerate extents', () => {
  const feature = (id, coordinates) => ({ id, geometry: { type: 'Point', coordinates }, properties: { name: id } });
  const result = projectLocations([feature('southwest', [78, 29]), feature('northeast', [80, 31]), feature('bad', [181, 0]), feature('missing', [null, 30])]);
  assert.equal(result.length, 2);
  assert.ok(result[0].x < result[1].x);
  assert.ok(result[0].y > result[1].y);
  assert.deepEqual(result[0].geometry.coordinates, [78, 29]);
  assert.equal(projectLocations([feature('one', [78, 30])])[0].x, 500);
});

test('empty/unavailable adapters never manufacture metrics', () => {
  assert.equal(number(null), 'DATA UNAVAILABLE');
  assert.ok(pageCards('tourism-intelligence', null).every(card => card.val === 'DATA UNAVAILABLE'));
  assert.ok(pageCards('simulation-results', null, null).every(card => card.val === 'DATA UNAVAILABLE'));
  assert.equal(pageCards('intervention-optimizer', null)[0].val, 'NOT AVAILABLE');
});

test('actual client round trip with saved models, data, scenarios and reports', { skip: !process.env.SAFARSAATHI_TEST_API }, async () => {
  const request = createClient(process.env.SAFARSAATHI_TEST_API, 30000);
  assert.equal((await request('/health')).status, 'ok');
  const models = await request('/models');
  assert.equal(models.length, 6);
  assert.equal((await request('/tourism/history')).series[1].observations.length, 72);
  assert.equal((await request('/destinations')).destinations.length, 29);
  assert.equal((await request('/map/layers')).features.length, 29);
  assert.equal((await request('/satellite/metadata')).scenes.length, 12);
  assert.ok((await request('/datasets?limit=2')).total > 900);
  for (const [path, body] of [
    ['/tourism/forecast', { destination: 'IND', horizon: 1 }],
    ['/tourism/monthly-forecast', { destination: 'IND', horizon: 1 }],
    ['/disaster/cyclone-count', { geography: 'NI', horizon: 1 }],
    ['/environment/pm25-forecast', { geography: 'IND', horizon: 1 }],
  ]) assert.ok(Number.isFinite((await request(path, { method: 'POST', body })).forecasts[0].prediction));
  const review = models.find(m => m.task === 'review classification');
  assert.equal((await request('/reviews/classify', { method: 'POST', body: { model_id: review.model_id, reviews: ['Helpful hotel staff.'] } })).predictions.length, 1);
  const payload = scenarioPayload({ baseline_visitors: 100, capacity: 120, demand_change_percent: 50, available_capacity_percent: 50 });
  const result = await request('/scenarios/simulate', { method: 'POST', body: payload });
  assert.equal(result.scenario.unserved_visitors, 90);
  assert.equal((await request('/reports/generate', { method: 'POST', body: { scenario: payload } })).scenario.scenario.unserved_visitors, 90);
  await assert.rejects(request('/optimization/solve', { method: 'POST', body: {} }), e => e.status === 501);
});
