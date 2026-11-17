// Single client for every SafarSaathi backend route. No mock data, no fallbacks:
// failures surface as ApiError so each page can say exactly what went wrong.

export class ApiError extends Error {
  constructor(message, { status = 0, kind = 'network', body = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.kind = kind; // network | timeout | unavailable | invalid | http | format | canceled
    this.body = body;
  }
}

export function resolveBase(configured) {
  const value = (configured ?? '').trim();
  if (!value) return '/api'; // same origin: backend or Vite dev proxy
  const url = new URL(value);
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error('VITE_SAFARSAATHI_API_URL must be a plain http(s) URL.');
  }
  return url.href.replace(/\/$/, '');
}

const env = typeof import.meta !== 'undefined' ? import.meta.env : undefined;
export const API_BASE = resolveBase(env?.VITE_SAFARSAATHI_API_URL);

export function createClient(base = API_BASE, timeoutMs = 30000, fetchImpl = (...a) => fetch(...a)) {
  return async function request(path, { method = 'GET', body, signal } = {}) {
    const controller = new AbortController();
    let timedOut = false;
    const onAbort = () => controller.abort();
    signal?.addEventListener('abort', onAbort, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    try {
      const response = await fetchImpl(base + path, {
        method, signal: controller.signal, credentials: 'omit',
        headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      let data;
      try { data = await response.json(); } catch {
        throw new ApiError(`The server answered ${response.status} without JSON. Check that the API URL points at the SafarSaathi backend.`, { status: response.status, kind: 'format' });
      }
      if (!response.ok) {
        const kind = [501, 503].includes(response.status) ? 'unavailable' : [400, 413, 415, 422].includes(response.status) ? 'invalid' : 'http';
        throw new ApiError(data?.detail || `Request failed with status ${response.status}.`, { status: response.status, kind, body: data });
      }
      return data;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timedOut) throw new ApiError('The backend took longer than 30 s. Free-tier hosts can take a minute to wake; try again.', { kind: 'timeout' });
      if (controller.signal.aborted) throw new ApiError('Request canceled.', { kind: 'canceled' });
      throw new ApiError(`Cannot reach the backend at ${base}. Start it with "python -m safarsaathi_ml.cli serve" or check the deployment URL.`, { kind: 'network' });
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', onAbort);
    }
  };
}

export const request = createClient();
const post = (path, body) => request(path, { method: 'POST', body });

// ---- validation mirrors backend bounds so users get instant, specific feedback
export function finiteInRange(raw, label, min, max) {
  const value = typeof raw === 'number' ? raw : typeof raw === 'string' && raw.trim() !== '' ? Number(raw) : NaN;
  if (!Number.isFinite(value) || value < min || value > max) throw new Error(`${label} must be a number between ${min.toLocaleString('en-IN')} and ${max.toLocaleString('en-IN')}.`);
  return value;
}

export function scenarioPayload(input) {
  return {
    baseline_visitors: finiteInRange(input.baseline_visitors, 'Baseline visitors', 0, 1e9),
    capacity: finiteInRange(input.capacity, 'Capacity', 1, 1e9),
    demand_change_percent: finiteInRange(input.demand_change_percent, 'Demand change', -100, 1000),
    available_capacity_percent: finiteInRange(input.available_capacity_percent, 'Available capacity', 0, 100),
  };
}

export function optimizationPayload({ demand, exposure_tradeoff, destinations, algorithm, seed, population, iterations }) {
  if (!Array.isArray(destinations) || destinations.length < 1 || destinations.length > 12) throw new Error('Add between 1 and 12 destinations.');
  const ids = new Set();
  const rows = destinations.map((d, i) => {
    const id = String(d.id ?? '').trim();
    if (!id || id.length > 64) throw new Error(`Destination ${i + 1} needs a name of 1–64 characters.`);
    if (ids.has(id)) throw new Error(`Destination names must be unique; "${id}" is repeated.`);
    ids.add(id);
    return {
      id,
      capacity: finiteInRange(d.capacity, `${id}: capacity`, 0, 1e9),
      accessibility: finiteInRange(d.accessibility, `${id}: accessibility`, 0, 1),
      road_capacity: finiteInRange(d.road_capacity, `${id}: road capacity`, 0, 1e9),
      resource_capacity: finiteInRange(d.resource_capacity, `${id}: resource capacity`, 0, 1e9),
      exposure_weight: finiteInRange(d.exposure_weight, `${id}: exposure weight`, 0, 1),
    };
  });
  const int = (raw, label, min, max) => {
    const v = finiteInRange(raw, label, min, max);
    if (!Number.isInteger(v)) throw new Error(`${label} must be a whole number.`);
    return v;
  };
  if (!['ga', 'pso'].includes(algorithm)) throw new Error('Choose GA or PSO.');
  return {
    problem: { demand: finiteInRange(demand, 'Total demand', 0, 1e9), exposure_tradeoff: finiteInRange(exposure_tradeoff, 'Exposure trade-off', 0, 1), destinations: rows },
    algorithm, seed: int(seed, 'Seed', 0, 4294967295), population: int(population, 'Population', 8, 64), iterations: int(iterations, 'Iterations', 1, 100),
  };
}

export function validateFloodTile(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('The file must be a JSON object with "image" and "metadata".');
  const keys = Object.keys(input).sort().join(',');
  if (keys !== 'image,metadata') throw new Error('The JSON must contain exactly "image" and "metadata".');
  const { image, metadata } = input;
  if (!Array.isArray(image) || image.length !== 128 || image.some(r => !Array.isArray(r) || r.length !== 128 || r.some(p => !Array.isArray(p) || p.length !== 2 || !p.every(v => Number.isFinite(v) && Math.abs(v) <= 10)))) {
    throw new Error('"image" must be a 128 × 128 × 2 array of finite values with |value| ≤ 10 (STURM-preprocessed VV/VH).');
  }
  if (metadata?.source_format !== 'STURM-S1-preprocessed') throw new Error('metadata.source_format must be "STURM-S1-preprocessed".');
  return input;
}

export const api = {
  health: () => request('/health'),
  release: () => request('/release'),
  twinMetadata: () => request('/twin/metadata'),
  twinState: body => request('/twin/state', { method: 'POST', body }),
  interventions: body => request('/twin/interventions', { method: 'POST', body }),
  anomalies: () => request('/anomalies'),
  hotspots: ({ year, method, eps_km, min_samples, k }) => request(`/hotspots?year=${year}&method=${method}&eps_km=${eps_km}&min_samples=${min_samples}&k=${k}`),
  routingMetadata: () => request('/routing/metadata'),
  route: body => request('/routing/route', { method: 'POST', body }),
  models: () => request('/models'),
  model: id => request(`/models/${encodeURIComponent(id)}`),
  capabilities: () => request('/capabilities'),
  systemSummary: () => request('/system/summary'),
  integrationStatus: () => request('/integration/status'),
  deploymentStatus: () => request('/deployment/status'),
  research: () => request('/research/status'),
  history: () => request('/tourism/history'),
  annualForecast: horizon => post('/tourism/forecast', { destination: 'IND', horizon }),
  monthlyForecast: horizon => post('/tourism/monthly-forecast', { destination: 'IND', horizon }),
  destinations: () => request('/destinations'),
  destination: id => request(`/destinations/${encodeURIComponent(id)}`),
  climate: id => request(`/destinations/${encodeURIComponent(id)}/climate`),
  layers: () => request('/map/layers'),
  satellite: () => request('/satellite/metadata'),
  datasets: (offset = 0, limit = 25, category = '') => request(`/datasets?offset=${offset}&limit=${limit}${category ? `&category=${encodeURIComponent(category)}` : ''}`),
  indicatorMetadata: () => request('/stress/indicator-metadata'),
  indicators: (geography, year) => post('/stress/indicators', { geography, year }),
  pm25Forecast: () => post('/environment/pm25-forecast', { geography: 'IND', horizon: 1 }),
  stressPredict: () => post('/stress/predict', {}),
  cycloneForecast: horizon => post('/disaster/cyclone-count', { geography: 'NI', horizon }),
  disasterPredict: () => post('/disaster/predict', {}),
  segment: tile => post('/flood/segment', tile),
  classify: (model_id, reviews) => post('/reviews/classify', { model_id, reviews }),
  simulate: input => post('/scenarios/simulate', input),
  optimizationMetadata: () => request('/optimization/metadata'),
  optimize: input => post('/optimization/allocate', input),
  operationalOptimizer: () => post('/optimization/solve', {}),
  report: ({ scenario, optimization } = {}) => post('/reports/generate', {
    ...(scenario ? { scenario } : {}), ...(optimization ? { optimization } : {}),
  }),
};

// ---- formatting
export const fmt = (value, digits = 2) => typeof value === 'number' && Number.isFinite(value)
  ? value.toLocaleString('en-IN', { maximumFractionDigits: digits }) : '—';
export const compact = value => typeof value === 'number' && Number.isFinite(value)
  ? new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(value) : '—';
export const bytes = n => {
  if (!Number.isFinite(n)) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; let v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
  return `${v.toFixed(v >= 100 || i === 0 ? 0 : 1)} ${units[i]}`;
};
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const monthLabel = ym => { const [y, m] = String(ym).split('-'); return m ? `${MONTHS[Number(m) - 1]} ${y}` : String(ym); };
export const download = (filename, data) => {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement('a'), { href: url, download: filename });
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
