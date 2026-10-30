import { request } from './client.js';

const post = (path, body) => request(path, { method: 'POST', body });
export const api = {
  health: () => request('/health'),
  models: () => request('/models'),
  model: id => request(`/models/${encodeURIComponent(id)}`),
  capabilities: () => request('/capabilities'),
  history: () => request('/tourism/history'),
  destinations: () => request('/destinations'),
  layers: () => request('/map/layers'),
  satellite: () => request('/satellite/metadata'),
  datasets: (offset = 0, limit = 20) => request(`/datasets?offset=${offset}&limit=${limit}`),
  indicatorMetadata: () => request('/stress/indicator-metadata'),
  indicators: (geography, year) => post('/stress/indicators', { geography, year: Number(year) }),
  annualForecast: horizon => post('/tourism/forecast', { destination: 'IND', horizon: Number(horizon) }),
  monthlyForecast: horizon => post('/tourism/monthly-forecast', { destination: 'IND', horizon: Number(horizon) }),
  cycloneForecast: horizon => post('/disaster/cyclone-count', { geography: 'NI', horizon: Number(horizon) }),
  pm25Forecast: () => post('/environment/pm25-forecast', { geography: 'IND', horizon: 1 }),
  classify: (model_id, reviews) => post('/reviews/classify', { model_id, reviews }),
  segment: input => post('/flood/segment', input),
  simulate: input => post('/scenarios/simulate', input),
  report: scenario => post('/reports/generate', scenario ? { scenario: scenario.parameters } : {}),
  optimizationAvailability: () => post('/optimization/solve', {}),
};

export async function overviewData() {
  // Independent failures must not replace available data or crash the entire view.
  const names = ['history', 'destinations', 'datasets', 'models', 'health'];
  const values = await Promise.allSettled(names.map(name => name === 'datasets' ? api.datasets(0, 1) : api[name]()));
  return Object.fromEntries(values.map((result, i) => [names[i], result.status === 'fulfilled'
    ? { data: result.value } : { error: result.reason.message }]));
}

export const pageLoaders = {
  'tourism-intelligence': api.history,
  'crowd-destination-stress': api.indicatorMetadata,
  'risk-resilience': api.capabilities,
  'live-geospatial-map': api.layers,
  'satellite-intelligence': api.satellite,
  'ai-model-center': () => Promise.all([api.models(), api.capabilities()]).then(([models, capabilities]) => ({ models, capabilities })),
  'tourist-community-insights': api.models,
  'data-hub': () => api.datasets(),
  'reports-briefs': api.health,
  'help-architecture': api.health,
};
