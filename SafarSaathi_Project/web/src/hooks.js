import { createContext, useCallback, useContext, useEffect, useRef, useState, useSyncExternalStore } from 'react';

// ---- tiny read cache so revisiting a page doesn't refetch large payloads
const cache = new Map();
const TTL = 5 * 60 * 1000;

export function useQuery(key, loader, { enabled = true } = {}) {
  const [state, setState] = useState(() => {
    const hit = key && cache.get(key);
    return hit && hit.expires > Date.now() ? { data: hit.data, error: null, loading: false } : { data: null, error: null, loading: enabled && !!key };
  });
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  useEffect(() => {
    if (!enabled || !key) return undefined;
    const hit = cache.get(key);
    if (nonce === 0 && hit && hit.expires > Date.now()) { setState({ data: hit.data, error: null, loading: false }); return undefined; }
    let live = true;
    setState(s => ({ data: s.data, error: null, loading: true }));
    loaderRef.current().then(data => {
      cache.set(key, { data, expires: Date.now() + TTL });
      if (live) setState({ data, error: null, loading: false });
    }).catch(error => { if (live) setState({ data: null, error, loading: false }); });
    return () => { live = false; };
  }, [key, nonce, enabled]);
  const retry = useCallback(() => { cache.delete(key); setNonce(n => n + 1); }, [key]);
  return { ...state, retry };
}

export function useAction() {
  const [state, setState] = useState({ data: null, error: null, loading: false });
  const mounted = useRef(true);
  useEffect(() => () => { mounted.current = false; }, []);
  const run = useCallback(async task => {
    setState(s => ({ data: s.data, error: null, loading: true }));
    try {
      const data = await task();
      if (mounted.current) setState({ data, error: null, loading: false });
      return data;
    } catch (error) {
      if (mounted.current) setState({ data: null, error, loading: false });
      return undefined;
    }
  }, []);
  const reset = useCallback(() => setState({ data: null, error: null, loading: false }), []);
  return { ...state, run, reset };
}

// ---- hash router: works on any static host and on the backend's SPA fallback
const subscribe = cb => { window.addEventListener('hashchange', cb); return () => window.removeEventListener('hashchange', cb); };
const snapshot = () => window.location.hash.replace(/^#\/?/, '') || 'home';
export function useRoute() {
  const raw = useSyncExternalStore(subscribe, snapshot, () => 'home');
  const [path, query = ''] = raw.split('?');
  const [page, ...rest] = path.split('/');
  return { page, param: rest.join('/') || null, query: new URLSearchParams(query) };
}
export const navigate = to => { window.location.hash = `/${to}`; };

// ---- session results shared across pages (scenario + optimisation feed Reports)
export const SessionContext = createContext(null);
export function useSessionState() {
  const [scenarios, setScenarios] = useState([]);
  const [optimization, setOptimization] = useState(null);
  const addScenario = useCallback(result => setScenarios(list => [{ ...result, ranAt: new Date().toISOString() }, ...list].slice(0, 8)), []);
  return { scenarios, addScenario, clearScenarios: () => setScenarios([]), optimization, setOptimization };
}
export const useSession = () => useContext(SessionContext);
