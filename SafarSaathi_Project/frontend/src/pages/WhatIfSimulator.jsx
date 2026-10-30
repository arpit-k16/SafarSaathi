import React, { useState } from 'react';
import { api } from '../services/api/resources.js';
import { scenarioPayload, number } from '../services/api/adapters.js';
import { useApiAction } from '../hooks/useApi.js';
import ApiState, { Limitations } from '../components/ApiState.jsx';
import { ScenarioDetails } from '../components/IntegrationDetails.jsx';

const HW_STATES = [
  { id: 0, status: 'NH-58 Open (Nominal 2-Lane)', sub: 'Unrestricted transit flow', capacity: '1,050 PCU/hr', factor: 1.0 },
  { id: 1, status: 'NH-58 1-Lane Severance', sub: 'Kaudiyala Sector Km 66 (Slump Zone)', capacity: '480 PCU/hr', factor: 2.2 },
  { id: 2, status: 'NH-58 Complete Dual Blockade', sub: 'Totaghati Massive Rockfall Zone', capacity: '0 PCU/hr (Gridlock)', factor: 5.0 },
];

export default function WhatIfSimulator({ onNavigate, showToast, lastScenario, onScenario }) {
  const [surgePercent, setSurgePercent] = useState(20); // +20%
  const [rainMm, setRainMm] = useState(45); // 45 mm/hr
  const [hwIndex, setHwIndex] = useState(1); // 1-Lane severance default
  const [accomPreset, setAccomPreset] = useState('nominal'); // 'nominal' | 'emergency' | 'degraded'
  const [fleetReady, setFleetReady] = useState(true);

  const [baselineVisitors, setBaselineVisitors] = useState('42000');
  const [capacity, setCapacity] = useState('50000');
  const [availability, setAvailability] = useState('100');
  const action = useApiAction();
  const result = action.loading || action.error ? null : lastScenario;
  const ratio = result?.scenario.utilization_ratio;
  const simulationResults = {
    totalPax: result?.scenario.visitors,
    additionalPax: result ? result.scenario.visitors - result.baseline.visitors : null,
    utilizationPercent: typeof ratio === 'number' ? ratio * 100 : null,
    servedVisitors: result?.scenario.served_visitors,
    unservedVisitors: result?.scenario.unserved_visitors,
    tier: result ? 'HYPOTHETICAL CAPACITY ACCOUNTING' : 'AWAITING SUBMISSION',
    tierColor: 'text-primary', tierBg: 'bg-primary/20 border-primary/40',
  };
  const handleRunSimulation = async () => {
    const response = await action.run(() => api.simulate(scenarioPayload({ baseline_visitors: baselineVisitors,
      capacity, demand_change_percent: surgePercent, available_capacity_percent: availability })));
    if (response) {
      onScenario(response);
      showToast({ title: 'Capacity scenario computed by backend', message: `Served ${number(response.scenario.served_visitors)}; unserved ${number(response.scenario.unserved_visitors)} visitor places. Hypothetical only.`, type: 'success' });
    }
  };

  return (
    <div data-page="what-if-simulator" className="flex flex-col w-full bg-surface text-on-surface">
      {/* Simulation Header */}
      <div className="px-gutter-lg pt-space-md pb-space-sm flex flex-col md:flex-row md:items-center justify-between gap-space-sm border-b border-white/5">
        <div className="flex items-center gap-space-sm flex-wrap">
          <div className="flex items-center gap-space-xs px-2 py-0.5 rounded bg-surface-container-high text-primary font-telemetry-sm text-telemetry-sm tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
            <span>WHAT-IF CAPACITY SCENARIO</span>
          </div>
          <span className="text-on-surface-variant font-telemetry-sm text-telemetry-sm tracking-widest text-xs">
            // USER-ASSUMED INPUTS · NO GEOGRAPHIC IMPACT MODEL
          </span>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <span className="text-slate-400">CALCULATION:</span>
          <span className="px-2 py-0.5 rounded bg-surface-container-high text-primary font-bold">
            ONE-PERIOD CAPACITY ACCOUNTING
          </span>
        </div>
      </div>

      {/* Main Split Grid: Left 5-Cols Parameter Controls + Right 7-Cols Dynamic Analytical Projections */}
      <div className="px-gutter-lg py-space-md pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md">
          
          {/* Left Parameter Engine: 5 Columns */}
          <div className="lg:col-span-5 flex flex-col gap-space-md bg-surface-container-lowest p-space-md rounded-xl border border-[#d4af37]/25 shadow-xl">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <span className="font-label-caps text-label-caps text-on-surface uppercase tracking-wider text-xs font-bold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[18px] text-primary">tune</span>
                <span>SCENARIO CONTROLS</span>
              </span>
              <button
                type="button"
                onClick={() => {
                  setSurgePercent(0);
                  setRainMm(15);
                  setHwIndex(0);
                  setAccomPreset('nominal');
                  setFleetReady(true);
                  setBaselineVisitors('42000'); setCapacity('50000'); setAvailability('100');
                }}
                className="text-[10px] font-mono text-slate-400 hover:text-primary transition-colors"
              >
                Reset Baseline
              </button>
            </div>

            <div className="flex flex-col gap-2 bg-surface-container p-3 rounded-lg border border-white/5 text-xs font-mono">
              <span className="text-primary">Explicit hypothetical inputs · same period / visitor places</span>
              <label>Baseline visitors <input aria-label="Baseline visitors" type="number" min="0" max="1000000000" required value={baselineVisitors} onChange={e => setBaselineVisitors(e.target.value)} className="w-full bg-surface-container-lowest border border-white/10 rounded p-2 mt-1" /></label>
              <label>Visitor capacity <input aria-label="Visitor capacity" type="number" min="1" max="1000000000" required value={capacity} onChange={e => setCapacity(e.target.value)} className="w-full bg-surface-container-lowest border border-white/10 rounded p-2 mt-1" /></label>
              <label>Available capacity (%) <input aria-label="Available capacity percent" type="number" min="0" max="100" required value={availability} onChange={e => setAvailability(e.target.value)} className="w-full bg-surface-container-lowest border border-white/10 rounded p-2 mt-1" /></label>
              <p className="text-slate-400">No observed destination capacity feed exists. Rainfall, highway state, accommodation presets and fleet controls below are retained as unmodeled demonstration context; only explicit inputs and tourist surge are submitted.</p>
            </div>
            {/* Parameter 1: Tourist Surge */}
            <div className="flex flex-col gap-1.5 bg-surface-container p-3 rounded-lg border border-white/5">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-slate-300 font-bold">1. Tourist Influx Surge</span>
                <span className="text-primary font-bold">+{surgePercent}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={surgePercent}
                onChange={(e) => setSurgePercent(Number(e.target.value))}
                className="w-full accent-primary bg-surface-container-highest cursor-pointer h-1.5 rounded"
              />
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>User-assumed baseline</span>
                <span className="text-primary font-semibold">+{number(simulationResults.additionalPax)} pax</span>
                <span>Max (+100%)</span>
              </div>
            </div>

            {/* Parameter 2: Rainfall Intensity */}
            <div className="flex flex-col gap-1.5 bg-surface-container p-3 rounded-lg border border-white/5">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-slate-300 font-bold">2. Convective Rainfall Intensity</span>
                <span className="text-secondary font-bold">{rainMm} mm/hr</span>
              </div>
              <input
                type="range"
                min="0"
                max="120"
                step="5"
                value={rainMm}
                onChange={(e) => setRainMm(Number(e.target.value))}
                className="w-full accent-secondary bg-surface-container-highest cursor-pointer h-1.5 rounded"
              />
              <div className="flex justify-between text-[10px] font-mono text-slate-400">
                <span>0 mm (Clear)</span>
                <span className={rainMm > 50 ? 'text-error font-bold' : 'text-slate-400'}>
                  Unmodeled context
                </span>
                <span>120 mm/hr</span>
              </div>
            </div>

            {/* Parameter 3: Highway State Stepper */}
            <div className="flex flex-col gap-1.5 bg-surface-container p-3 rounded-lg border border-white/5">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-slate-300 font-bold">3. Highway Transit State</span>
                <span className="text-primary font-mono text-[10px]">{HW_STATES[hwIndex].capacity}</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-surface-container-lowest border border-white/5 mt-1">
                <button
                  type="button"
                  onClick={() => setHwIndex(prev => Math.max(0, prev - 1))}
                  disabled={hwIndex === 0}
                  className="px-2 py-1 rounded bg-surface-container hover:bg-surface-container-high disabled:opacity-30 text-xs text-white"
                >
                  ◀
                </button>
                <div className="text-center">
                  <div className="text-xs font-bold text-white">{HW_STATES[hwIndex].status}</div>
                  <div className="text-[10px] text-slate-400">{HW_STATES[hwIndex].sub}</div>
                </div>
                <button
                  type="button"
                  onClick={() => setHwIndex(prev => Math.min(HW_STATES.length - 1, prev + 1))}
                  disabled={hwIndex === HW_STATES.length - 1}
                  className="px-2 py-1 rounded bg-surface-container hover:bg-surface-container-high disabled:opacity-30 text-xs text-white"
                >
                  ▶
                </button>
              </div>
            </div>

            {/* Parameter 4: Accommodation Presets */}
            <div className="flex flex-col gap-1.5 bg-surface-container p-3 rounded-lg border border-white/5">
              <div className="text-xs font-mono text-slate-300 font-bold">4. Shelter &amp; Accommodation State</div>
              <div className="grid grid-cols-3 gap-1.5 font-mono text-[10px] mt-1">
                {[
                  { id: 'nominal', label: 'Nominal 100%' },
                  { id: 'emergency', label: 'Camps +25%' },
                  { id: 'degraded', label: 'Outage -30%' },
                ].map(({ id, label }) => (
                  <button
                    key={id}
                    type="button"
                    onClick={() => setAccomPreset(id)}
                    className={`py-1.5 px-1 rounded transition-colors text-center ${
                      accomPreset === id
                        ? 'bg-primary text-on-primary font-bold shadow'
                        : 'bg-surface-container-lowest text-slate-400 hover:text-white'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Parameter 5: Emergency Fleet Toggle */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-container border border-white/5 text-xs font-mono">
              <span className="text-slate-300">Emergency Transit Fleet</span>
              <button
                type="button"
                onClick={() => setFleetReady(!fleetReady)}
                className={`px-3 py-1 rounded font-bold transition-colors ${
                  fleetReady ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40' : 'bg-red-950 text-red-400 border border-red-500/40'
                }`}
              >
                {fleetReady ? 'STANDBY READY' : 'FLEET COMMITTED'}
              </button>
            </div>

            {/* Run Button */}
            <button
              type="button"
              onClick={handleRunSimulation}
              disabled={action.loading}
              className="mt-2 w-full py-3 rounded-lg bg-gradient-to-r from-[#f2ca50] via-[#d4af37] to-[#b8860b] text-slate-950 font-bold text-xs uppercase font-mono tracking-wider shadow-lg glow-gold-btn transition-all"
            >
              {action.loading ? 'Processing backend scenario…' : 'Re-Calculate Simulation Matrix'}
            </button>
          </div>

          {/* Right Analytical Outputs: 7 Columns */}
          <div className="lg:col-span-7 flex flex-col gap-space-md">
            
            <ApiState {...action} />
            <p className="font-mono text-xs text-slate-400">Last successfully submitted parameters only. Changes to controls require recalculation. No scenario persistence service is available; results stay in this session until reload.</p>
            {/* Projected Impact Scorecard */}
            <div className="bg-surface-container-lowest p-space-md rounded-xl border border-[#d4af37]/25 shadow-xl">
              <div className="flex items-center justify-between border-b border-white/5 pb-2 mb-3">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs font-bold">
                  BACKEND SCENARIO OUTCOME
                </span>
                <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${simulationResults.tierBg} ${simulationResults.tierColor}`}>
                  {simulationResults.tier}
                </span>
              </div>

              {/* 3 Metric Readouts */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-mono">
                
                <div className="p-3 rounded-lg bg-surface-container border border-white/5 flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase">DEMAND / CAPACITY</span>
                  <div className={`text-3xl font-extrabold my-1 ${simulationResults.tierColor}`}>
                    {number(simulationResults.utilizationPercent)}
                    <span className="text-xs text-slate-400">%</span>
                  </div>
                  <span className="text-[9px] text-slate-400">Undefined when available capacity is zero</span>
                </div>

                <div className="p-3 rounded-lg bg-surface-container border border-white/5 flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase">SERVED VISITORS</span>
                  <div className="text-3xl font-extrabold my-1 text-white">
                    {number(simulationResults.servedVisitors)}
                    <span className="text-xs text-slate-400"> places</span>
                  </div>
                  <span className="text-[9px] text-slate-400">Returned capacity accounting</span>
                </div>

                <div className="p-3 rounded-lg bg-surface-container border border-white/5 flex flex-col">
                  <span className="text-[10px] text-slate-400 uppercase">UNSERVED VISITORS</span>
                  <div className="text-3xl font-extrabold my-1 text-amber-400">
                    {number(simulationResults.unservedVisitors)}
                  </div>
                  <span className="text-[9px] text-slate-400">Unmet hypothetical demand; not hazard exposure</span>
                </div>

              </div>

              {/* Stress Visual Progress Bar */}
              <div className="mt-4">
                <div className="flex justify-between text-[10px] font-mono mb-1">
                  <span className="text-slate-400">Demand / available capacity</span>
                  <span className={`font-bold ${simulationResults.tierColor}`}>{number(simulationResults.utilizationPercent)}% UTILIZATION</span>
                </div>
                <div className="w-full bg-surface-container-highest h-2 rounded overflow-hidden">
                  <div
                    className={`h-full rounded transition-all duration-500 ${
                      'bg-primary'
                    }`}
                    style={{ width: `${Math.min(100, simulationResults.utilizationPercent ?? 0)}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Simulated Vector Graph */}
            <div className="bg-surface-container-lowest p-space-md rounded-xl border border-[#d4af37]/25 shadow-xl flex flex-col gap-2">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs font-bold">
                DEMO CORRIDOR VECTOR · NOT A GEOGRAPHIC RESULT
              </span>

              <div className="p-3 bg-[#0a0c12] rounded border border-white/5">
                <svg className="w-full h-28 stroke-primary/70 fill-none" viewBox="0 0 320 100">
                  <path d="M 20 80 Q 80 40 150 50 T 280 20" strokeDasharray="4,4" strokeWidth="2"></path>
                  <circle className="fill-primary" cx="150" cy="50" r="5"></circle>
                  <text className="fill-on-surface-variant text-[9px] font-mono" x="140" y="70">Kaudiyala Km 66</text>
                  <circle className="fill-primary/60" cx="240" cy="30" r="4"></circle>
                  <text className="fill-on-surface-variant text-[8px] font-mono" x="210" y="22">Devprayag Confluence</text>
                </svg>
              </div>

              {/* Timeline Processing Steps */}
              <div className="grid grid-cols-3 gap-2 text-xs font-mono pt-1">
                <div className="p-2 rounded bg-surface-container border border-white/5">
                  <div className="text-primary font-bold text-[10px]">DEMO CONTEXT</div>
                  <div className="text-[10px] text-slate-300">No rainfall or slope model implemented</div>
                </div>
                <div className="p-2 rounded bg-surface-container border border-white/5">
                  <div className="text-secondary font-bold text-[10px]">DEMO CONTEXT</div>
                  <div className="text-[10px] text-slate-300">No queue or travel-delay calculation</div>
                </div>
                <div className="p-2 rounded bg-surface-container border border-white/5">
                  <div className="text-error font-bold text-[10px]">DEMO CONTEXT</div>
                  <div className="text-[10px] text-slate-300">No route-capacity or affected-location output</div>
                </div>
              </div>
            </div>

            {/* Optimal Action Recommendation */}
            <div className="bg-surface-container-lowest p-space-md rounded-xl border border-primary/30 shadow-xl flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[28px] text-primary">psychology</span>
                <div>
                  <div className="text-xs font-bold text-white">Scenario results & assumptions:</div>
                  <div className="text-[11px] text-slate-300">
                    Review the actual baseline and capacity outcomes below. Optimization and live dispatch are unavailable.
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => onNavigate('simulation-results')}
                className="px-4 py-2 rounded bg-primary text-on-primary font-bold text-xs font-mono hover:bg-[#ffe088] transition-colors whitespace-nowrap shadow"
              >
                View Simulation Results →
              </button>
            </div>

            <div className="bg-surface-container-lowest p-space-md rounded-xl border border-[#d4af37]/25 shadow-xl text-xs font-mono"><ScenarioDetails result={result} /><Limitations items={result ? [] : ['Run the backend scenario to display actual results. No frontend-generated forecast or stress score is used.']} /></div>
          </div>

        </div>
      </div>
    </div>
  );
}
