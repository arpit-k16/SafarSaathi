export class ApiError extends Error {
  constructor(message, { status = 0, kind = 'network' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.kind = kind;
  }
}

export function createClient(baseUrl = 'http://127.0.0.1:8000', timeoutMs = 20000) {
  const base = new URL(baseUrl);
  if (!['http:', 'https:'].includes(base.protocol) || base.username || base.password || base.search || base.hash) {
    throw new Error('API URL must be an HTTP(S) URL without credentials, query or fragment.');
  }
  const prefix = base.href.replace(/\/$/, '');
  return async function request(path, { method = 'GET', body, signal } = {}) {
    const controller = new AbortController();
    let timedOut = false;
    const abort = () => controller.abort();
    signal?.addEventListener('abort', abort, { once: true });
    if (signal?.aborted) controller.abort();
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    try {
      const response = await fetch(prefix + path, {
        method, signal: controller.signal, credentials: 'omit',
        headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      });
      let data;
      try { data = await response.json(); }
      catch { throw new ApiError('The API returned an invalid JSON response.', { status: response.status, kind: 'format' }); }
      if (!response.ok) throw new ApiError(data?.detail || `API request failed (${response.status}).`, {
        status: response.status, kind: [501, 503].includes(response.status) ? 'unavailable' : 'http',
      });
      return data;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (timedOut) throw new ApiError('Request timed out. Retry when the backend is ready.', { kind: 'timeout' });
      if (controller.signal.aborted) throw new ApiError('Request canceled.', { kind: 'canceled' });
      throw new ApiError('API unavailable. Check that the Python backend is running.', { kind: 'network' });
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
    }
  };
}

export const API_BASE_URL = import.meta.env?.VITE_SAFARSAATHI_API_URL || 'http://127.0.0.1:8000';
export const request = createClient(API_BASE_URL);

const cache = new Map();
export function cachedRead(key, loader, force = false) {
  const current = cache.get(key);
  if (current?.promise) return current.promise;
  if (!force && current && current.expires > Date.now()) return Promise.resolve(current.data);
  const entry = {};
  entry.promise = Promise.resolve().then(loader).then(data => {
    cache.set(key, { data, expires: Date.now() + 60000 });
    return data;
  }).catch(error => { cache.delete(key); throw error; });
  cache.set(key, entry);
  return entry.promise;
}
