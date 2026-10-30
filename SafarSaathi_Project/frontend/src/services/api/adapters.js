export const number = value => typeof value === 'number' && Number.isFinite(value)
  ? value.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : 'DATA UNAVAILABLE';

export function scenarioPayload(input) {
  const bounds = { baseline_visitors: [0, 1e9], capacity: [1, 1e9],
    demand_change_percent: [-100, 1000], available_capacity_percent: [0, 100] };
  const result = {};
  for (const [key, [min, max]] of Object.entries(bounds)) {
    const raw = input[key];
    const value = typeof raw === 'number' || (typeof raw === 'string' && raw.trim()) ? Number(raw) : NaN;
    if (!Number.isFinite(value) || value < min || value > max) throw new Error(`${key.replaceAll('_', ' ')} must be between ${min} and ${max}.`);
    result[key] = value;
  }
  return result;
}

export function projectLocations(features, width = 1000, height = 700) {
  const points = features.filter(f => f?.geometry?.type === 'Point' && Array.isArray(f.geometry.coordinates)
    && f.geometry.coordinates.length >= 2 && f.geometry.coordinates.slice(0, 2).every(Number.isFinite)
    && Math.abs(f.geometry.coordinates[0]) <= 180 && Math.abs(f.geometry.coordinates[1]) <= 90);
  if (!points.length) return [];
  const lons = points.map(f => f.geometry.coordinates[0]);
  const lats = points.map(f => f.geometry.coordinates[1]);
  const minX = Math.min(...lons), maxX = Math.max(...lons), minY = Math.min(...lats), maxY = Math.max(...lats);
  return points.map(f => ({ ...f,
    x: maxX === minX ? width / 2 : 45 + (f.geometry.coordinates[0] - minX) / (maxX - minX) * (width - 90),
    y: maxY === minY ? height / 2 : height - 45 - (f.geometry.coordinates[1] - minY) / (maxY - minY) * (height - 90),
  }));
}

const kpi = (label, val, sub) => ({ label, val: typeof val === 'number' ? number(val) : val, sub });
export function pageCards(tab, data, scenario) {
  const absent = () => Array.from({ length: 4 }, (_, i) => kpi(['STATUS', 'SOURCE', 'COVERAGE', 'OUTPUT'][i], 'DATA UNAVAILABLE', 'No fabricated fallback'));
  if (tab === 'simulation-results') return scenario ? [
    kpi('BASELINE VISITORS', scenario.baseline.visitors, 'User-assumed baseline'),
    kpi('SCENARIO VISITORS', scenario.scenario.visitors, 'Hypothetical demand'),
    kpi('SERVED VISITORS', scenario.scenario.served_visitors, 'Capacity accounting'),
    kpi('UNSERVED VISITORS', scenario.scenario.unserved_visitors, 'No exposure or injury inference'),
  ] : absent();
  if (tab.includes('optim')) return [kpi('ENGINE', 'NOT AVAILABLE', 'OPTIMIZATION ENGINE NOT AVAILABLE'),
    kpi('GA / PSO', 'NOT IMPLEMENTED', 'No candidate generated'), kpi('OBJECTIVE', 'NOT DEFINED', 'Validated costs/benefits needed'), kpi('OPTIMAL PLAN', 'UNAVAILABLE', 'No optimization claim')];
  if (!data) return absent();
  if (tab === 'tourism-intelligence') {
    const annual = data.series?.find(s => s.frequency === 'annual')?.observations || [];
    const monthly = data.series?.find(s => s.frequency === 'monthly')?.observations || [];
    return [kpi('ANNUAL ARRIVALS', annual.at(-1)?.arrivals, `${annual.at(-1)?.year ?? 'Unknown'} · India national`),
      kpi('MONTHLY FTA', monthly.at(-1)?.arrivals, `${monthly.at(-1)?.date ?? 'Unknown'} · excludes NRI`),
      kpi('ANNUAL OBSERVATIONS', annual.length, 'World Bank ST.INT.ARVL'), kpi('MONTHLY OBSERVATIONS', monthly.length, 'Ministry of Tourism · historical')];
  }
  if (tab === 'data-hub') return [kpi('LOCAL FILES', data.total, 'File count, not records'), kpi('SOURCE GROUPS', Object.keys(data.groups || {}).length, 'Local file inventory'),
    kpi('PAGE FILES', data.files?.length ?? 0, 'Paginated metadata'), kpi('LIVE CONNECTORS', 'NOT CONFIGURED', 'No external freshness claim')];
  if (tab === 'satellite-intelligence') return [kpi('LOCAL SCENES', data.scenes?.length ?? 0, 'Raw imagery metadata only'),
    kpi('SENTINEL-1', data.scenes?.filter(s => s.mission === 'sentinel1').length ?? 0, 'Acquisition parsed from ID'),
    kpi('SENTINEL-2', data.scenes?.filter(s => s.mission === 'sentinel2').length ?? 0, 'No raw-scene analysis'), kpi('LIVE DETECTION', 'UNAVAILABLE', 'Separate STURM benchmark input only')];
  if (tab === 'ai-model-center') return [kpi('REGISTERED ARTIFACTS', data.models?.length ?? 0, 'Loading is not accuracy validation'),
    kpi('MODEL METRICS', 'RECORDED', 'Historical evaluations'), kpi('LIVE WARNINGS', 'NOT IMPLEMENTED', 'Experimental scope only'), kpi('TRAINING ON REQUEST', 'DISABLED', 'Persisted pipelines')];
  if (tab === 'crowd-destination-stress') return [kpi('STRESS MODEL', 'NOT IMPLEMENTED', 'STRESS MODEL NOT IMPLEMENTED'),
    kpi('GEOGRAPHIES', data.geographies?.length ?? 0, 'Historical indicators'), kpi('OBSERVED YEARS', data.years?.length ?? 0, 'Source-specific coverage'), kpi('LOCAL CROWD FEED', 'UNAVAILABLE', 'No arbitrary stress scores')];
  if (tab === 'risk-resilience') return [kpi('BROAD HAZARD MODEL', 'UNAVAILABLE', 'No live emergency warning'), kpi('ARCHIVE FORECAST', 'NI BASIN', 'User-run cyclone count forecast'),
    kpi('EXPOSURE OVERLAY', 'NOT IMPLEMENTED', 'No live local observations'), kpi('SCOPE', 'EXPERIMENTAL', 'Historical archive counts only')];
  if (tab === 'live-geospatial-map') return [kpi('SOURCE LOCATIONS', data.features?.length ?? 0, 'Static NASA POWER grid points'),
    kpi('COORDINATES', 'LON / LAT', 'Source-native; no EPSG declaration'), kpi('SENSOR TELEMETRY', 'UNAVAILABLE', 'No GPS or IoT synchronization'), kpi('ROAD LAYERS', 'DEMO DATA', 'No operational road graph')];
  if (tab === 'tourist-community-insights') return [kpi('REVIEW MODELS', data.filter(m => m.task === 'review classification').length, 'Saved source-domain classifier'),
    kpi('OUTPUT', 'BINARY LABEL', 'Positive / negative only'), kpi('LOCAL CORPUS', 'NOT AVAILABLE', 'Global hotel-review domain'), kpi('INFERENCE', 'ON REQUEST', 'No automatic text submission')];
  return [kpi('BACKEND', data.status || 'AVAILABLE', data.service || 'Local Python API'), kpi('ARTIFACTS', data.trained_models, 'Registered count'),
    kpi('LIVE OPERATIONS', 'UNAVAILABLE', 'No dispatch integration'), kpi('PDF EXPORT', 'COMING SOON', 'JSON reports available')];
}
