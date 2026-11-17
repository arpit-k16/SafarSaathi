import React, { Suspense, lazy, useEffect, useState } from 'react';
import { API_BASE, api } from './api.js';
import { SessionContext, navigate, useQuery, useRoute, useSessionState } from './hooks.js';
import { Loading } from './components/ui.jsx';

const Landing = lazy(() => import('./pages/Landing.jsx'));

const pages = {
  overview: lazy(() => import('./pages/Overview.jsx')),
  tourism: lazy(() => import('./pages/Tourism.jsx')),
  destinations: lazy(() => import('./pages/Destinations.jsx')),
  hazards: lazy(() => import('./pages/Hazards.jsx')),
  flood: lazy(() => import('./pages/Flood.jsx')),
  environment: lazy(() => import('./pages/Environment.jsx')),
  satellite: lazy(() => import('./pages/Satellite.jsx')),
  reviews: lazy(() => import('./pages/Reviews.jsx')),
  scenarios: lazy(() => import('./pages/Scenarios.jsx')),
  optimizer: lazy(() => import('./pages/Optimizer.jsx')),
  models: lazy(() => import('./pages/Models.jsx')),
  'data-hub': lazy(() => import('./pages/DataHub.jsx')),
  reports: lazy(() => import('./pages/Reports.jsx')),
  system: lazy(() => import('./pages/System.jsx')),
  twin: lazy(() => import('./pages/Twin.jsx')),
  hotspots: lazy(() => import('./pages/Hotspots.jsx')),
  routing: lazy(() => import('./pages/Routing.jsx')),
};

export const NAV = [
  { group: null, items: [['overview', 'Overview']] },
  { group: 'Demand and places', items: [['tourism', 'Tourism demand'], ['destinations', 'Destinations and climate'], ['hotspots', 'Hotspots and anomalies']] },
  { group: 'Risk', items: [['hazards', 'Cyclone archive'], ['flood', 'Flood segmentation'], ['environment', 'Environment and pressure'], ['satellite', 'Satellite archive'], ['routing', 'Risk-aware routing']] },
  { group: 'Visitors', items: [['reviews', 'Review insights']] },
  { group: 'Planning', items: [['twin', 'Digital twin and stress'], ['scenarios', 'Capacity scenarios'], ['optimizer', 'Allocation optimizer']] },
  { group: 'Evidence', items: [['models', 'Model center'], ['data-hub', 'Data hub'], ['reports', 'Reports'], ['system', 'System and API']] },
];

class PageBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="mx-auto max-w-[70ch] px-8 py-12">
        <h1 className="text-2xl font-semibold">This page hit an unexpected response</h1>
        <p className="mt-2 text-mist">The rest of the console still works. Reload to try again; if it keeps happening, the backend may have returned data in an unexpected shape.</p>
        <pre className="mt-4 overflow-auto rounded-lg border border-line bg-slate p-3 font-mono text-xs text-ember">{String(this.state.error?.message || this.state.error)}</pre>
        <button type="button" className="mt-4 rounded-lg bg-gold px-4 py-2 text-sm font-semibold text-ink" onClick={() => window.location.reload()}>Reload</button>
      </div>
    );
  }
}

function BackendStatus() {
  const q = useQuery('health', api.health);
  const ok = q.data?.status === 'ok';
  return (
    <div className="flex items-center gap-2 text-xs text-mist" title={`API base: ${API_BASE}`}>
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-moss' : q.loading ? 'bg-gold animate-pulse' : 'bg-ember'}`} aria-hidden />
      {ok ? `Backend online · ${q.data.trained_models} saved models` : q.loading ? 'Connecting to backend…' : 'Backend offline'}
      {!ok && !q.loading && <button type="button" className="ml-auto text-gold hover:underline" onClick={q.retry}>Retry</button>}
    </div>
  );
}

function Sidebar({ page, open, onClose }) {
  return (
    <>
      <div className={`fixed inset-0 z-30 bg-black/60 md:hidden ${open ? '' : 'hidden'}`} onClick={onClose} aria-hidden />
      <aside className={`no-print fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-slate transition-transform md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <a href="#/" className="flex items-center gap-3 px-5 pb-5 pt-6" onClick={onClose}>
          <img src="/logo-mark.png" alt="" className="h-10 w-10" />
          <span>
            <span className="block font-display text-lg font-semibold leading-tight text-snow">SafarSaathi</span>
            <span className="block text-xs leading-snug text-mist">Tourism Intelligence &amp; Resilience Platform</span>
          </span>
        </a>
        <nav className="scroll-thin flex-1 overflow-y-auto px-3 pb-4" aria-label="Sections">
          {NAV.map(section => (
            <div key={section.group || 'root'} className="mb-4">
              {section.group && <div className="px-3 pb-1 text-xs font-medium text-mist/80">{section.group}</div>}
              {section.items.map(([id, label]) => {
                const active = page === id;
                return (
                  <a key={id} href={`#/${id}`} onClick={onClose} aria-current={active ? 'page' : undefined}
                    className={`relative block rounded-lg px-3 py-1.5 text-[14px] transition-colors ${active ? 'bg-gold/10 font-semibold text-gold' : 'text-snow/85 hover:bg-ridge hover:text-snow'}`}>
                    {active && <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-gold" aria-hidden />}
                    {label}
                  </a>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="border-t border-line px-5 py-4"><BackendStatus /></div>
      </aside>
    </>
  );
}

export default function App() {
  const route = useRoute();
  const session = useSessionState();
  const [menu, setMenu] = useState(false);
  const Page = pages[route.page];
  const isHome = route.page === 'home';
  useEffect(() => { if (!Page && !isHome) navigate('overview'); }, [Page, isHome]);
  useEffect(() => {
    const title = NAV.flatMap(s => s.items).find(([id]) => id === route.page)?.[1];
    document.title = title ? `${title} · SafarSaathi` : 'SafarSaathi · AI-Powered Tourism Intelligence & Resilience Platform';
    window.scrollTo(0, 0);
  }, [route.page]);
  if (isHome) {
    return (
      <Suspense fallback={<div className="px-8 py-10"><Loading label="Loading…" /></div>}>
        <Landing />
      </Suspense>
    );
  }
  return (
    <SessionContext.Provider value={session}>
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-gold focus:px-3 focus:py-2 focus:text-ink">Skip to content</a>
      <Sidebar page={route.page} open={menu} onClose={() => setMenu(false)} />
      <div className="md:pl-64">
        <div className="contours no-print sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-line bg-ink/90 px-5 backdrop-blur md:px-8">
          <button type="button" className="rounded-lg border border-line px-3 py-1.5 text-sm md:hidden" onClick={() => setMenu(true)} aria-label="Open navigation">Menu</button>
          <span className="text-sm text-mist">Uttarakhand and India · historical evidence and research models</span>
        </div>
        <main id="main">
          <Suspense fallback={<div className="px-8 py-10"><Loading label="Loading page…" /></div>}>
            {Page ? <PageBoundary key={route.page}><Page route={route} /></PageBoundary> : null}
          </Suspense>
        </main>
      </div>
    </SessionContext.Provider>
  );
}
