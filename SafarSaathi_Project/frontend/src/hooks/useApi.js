import { useCallback, useEffect, useRef, useState } from 'react';
import { cachedRead } from '../services/api/client.js';

export function useApiQuery(key, loader) {
  const [state, setState] = useState({ data: null, loading: !!loader, error: null });
  const [revision, setRevision] = useState(0);
  const loaderRef = useRef(loader);
  useEffect(() => { loaderRef.current = loader; });
  useEffect(() => {
    let active = true;
    if (!loaderRef.current) { setState({ data: null, loading: false, error: null }); return; }
    setState({ data: null, loading: true, error: null });
    cachedRead(key, loaderRef.current, revision > 0).then(data => {
      if (active) setState({ data, loading: false, error: null });
    }).catch(error => { if (active) setState({ data: null, loading: false, error }); });
    return () => { active = false; };
  }, [key, revision]);
  const retry = useCallback(() => setRevision(r => r + 1), []);
  return { ...state, retry };
}

export function useApiAction() {
  const [state, setState] = useState({ data: null, loading: false, error: null });
  const active = useRef(true);
  const busy = useRef(false);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  const run = useCallback(async task => {
    if (busy.current) return undefined;
    busy.current = true;
    setState({ data: null, loading: true, error: null });
    try {
      const data = await task();
      if (active.current) setState({ data, loading: false, error: null });
      return active.current ? data : undefined;
    } catch (error) {
      if (active.current) setState({ data: null, loading: false, error });
      return undefined;
    } finally { busy.current = false; }
  }, []);
  return { ...state, run };
}
