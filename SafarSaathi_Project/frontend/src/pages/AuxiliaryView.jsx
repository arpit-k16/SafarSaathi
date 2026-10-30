import React, { useState } from 'react';
import { useApiQuery } from '../hooks/useApi.js';
import { api, pageLoaders } from '../services/api/resources.js';
import { pageCards } from '../services/api/adapters.js';
import ApiState from '../components/ApiState.jsx';
import IntegrationDetails from '../components/IntegrationDetails.jsx';

const TITLES = {
  'tourism-intelligence': 'Tourism Intelligence & Demographics',
  'crowd-destination-stress': 'Crowd & Destination Stress Analysis',
  'risk-resilience': 'Geotechnical & Climate Risk Resilience',
  'live-geospatial-map': 'Live Geospatial Map & Sensor Telemetry',
  'satellite-intelligence': 'Satellite Remote Sensing & Earth Observation',
  'ai-model-center': 'AI Model Center & Predictive Neural Nets',
  'help-architecture': 'System Architecture & CSIR-NDMA Specification',
};

export default function AuxiliaryView({ activeTab, onNavigate, lastScenario }) {
  const [page, setPage] = useState(0);
  const loader = activeTab === 'data-hub' ? () => api.datasets(page * 20, 20) : pageLoaders[activeTab];
  const query = useApiQuery(`${activeTab}:${page}`, loader);
  const config = {
    title: TITLES[activeTab] || activeTab.replaceAll('-', ' ').toUpperCase(),
    sub: 'Local backend responses with source scope, recorded periods and explicit availability. No live telemetry is configured.',
    kpis: pageCards(activeTab, query.data, lastScenario),
  };
  return (
    <div data-page={activeTab} className="flex flex-col w-full bg-surface text-on-surface p-gutter-lg pb-12">
      {/* Header */}
      <div className="border-b border-white/5 pb-4 mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/30 uppercase font-bold">
              BACKEND INTELLIGENCE
            </span>
            <span className="text-xs font-mono text-slate-400">// {activeTab.toUpperCase()}</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">{config.title}</h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl">{config.sub}</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onNavigate('overview')}
            className="px-3 py-1.5 rounded bg-surface-container hover:bg-surface-container-high border border-white/10 text-xs font-mono text-slate-300 hover:text-primary transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[16px]">dashboard</span>
            <span>Return to Overview</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {config.kpis.map((kpi, idx) => (
          <div key={idx} className="bg-surface-container-lowest p-4 rounded-xl border border-[#d4af37]/20 shadow-lg">
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
              {kpi.label}
            </span>
            <div className="text-2xl font-extrabold text-white font-mono tracking-tight my-1">
              {query.loading ? 'Loading…' : kpi.val}
            </div>
            <span className="text-[10px] font-mono text-primary">{kpi.sub}</span>
          </div>
        ))}
      </div>

      {/* Detailed Analysis Deck */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 min-w-0 bg-surface-container-lowest rounded-xl border border-[#d4af37]/20 p-6 shadow-xl">
          <span className="font-label-caps text-label-caps text-on-surface uppercase tracking-wider text-xs font-bold block mb-4">
            SOURCE RECORDS &amp; ANALYSIS
          </span>
          <div className="bg-[#080a0f] p-4 rounded-lg border border-white/5 font-mono text-xs text-slate-300 flex flex-col gap-2 min-w-0 break-words">
            <ApiState {...query}>
              {!query.loading && !query.error && <IntegrationDetails tab={activeTab} data={query.data} lastScenario={lastScenario} page={page} setPage={setPage} />}
            </ApiState>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl border border-[#d4af37]/20 p-6 shadow-xl flex flex-col justify-between">
          <div>
            <span className="font-label-caps text-label-caps text-on-surface uppercase tracking-wider text-xs font-bold block mb-2">
              DISPATCH SHORTCUTS
            </span>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Navigate the existing analysis views. Session scenarios appear in Simulation Results; no live dispatch is performed.
            </p>
            <div className="flex flex-col gap-2 font-mono text-xs">
              <button
                type="button"
                onClick={() => onNavigate('what-if-simulator')}
                className="w-full py-2.5 px-3 rounded bg-surface-container hover:bg-surface-container-high border border-white/10 hover:border-primary text-slate-200 hover:text-primary transition-all text-left flex items-center justify-between"
              >
                <span>Simulate Influx Choke</span>
                <span>→</span>
              </button>
              <button
                type="button"
                onClick={() => onNavigate('destination-twin')}
                className="w-full py-2.5 px-3 rounded bg-surface-container hover:bg-surface-container-high border border-white/10 hover:border-primary text-slate-200 hover:text-primary transition-all text-left flex items-center justify-between"
              >
                <span>Inspect Micro-Precinct Twin</span>
                <span>→</span>
              </button>
              <button
                type="button"
                onClick={() => onNavigate('disaster-mode')}
                className="w-full py-2.5 px-3 rounded bg-red-950/40 hover:bg-red-900/50 border border-red-500/40 text-red-200 transition-all text-left flex items-center justify-between shadow-[0_0_12px_rgba(239,68,68,0.2)]"
              >
                <span>Open Simulation Exercise</span>
                <span>→</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
