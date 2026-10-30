import React, { useState } from 'react';
import { ScenarioDetails } from '../components/IntegrationDetails.jsx';

export default function DisasterMode({ onNavigate, showToast, lastScenario }) {
  const [actions, setActions] = useState({
    haltIngress: true,
    tehriBypass: true,
    smsBroadcast: true,
    heliEvac: false,
    powerIsolate: false,
  });

  const toggleAction = (key) => {
    setActions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const authorizedCount = Object.values(actions).filter(Boolean).length;

  const handleAuthorizeBrief = () => {
    showToast({
      title: 'Simulation Protocol Brief Generated',
      message: `${authorizedCount} local exercise actions selected. No dispatch, SMS, authorization or protocol archive is connected.`,
      type: 'warning',
    });
  };

  return (
    <div data-page="disaster-mode" className="flex flex-col w-full bg-[#080709] text-on-surface">
      {/* Persistent Simulation Safety Banner */}
      <div className="bg-red-950/80 border-b border-red-500/40 px-gutter-lg py-2 flex items-center justify-between text-xs font-mono text-red-200">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-ping shadow-[0_0_8px_#ef4444]"></span>
          <span className="font-bold text-red-100">SIMULATION MODE — NOT A LIVE EMERGENCY ALERT. ALL TACTICAL PANELS: DEMO DATA.</span>
        </div>
        <span className="text-[10px] text-red-300 hidden md:inline">
          CSIR-NDMA DRILL PROTOCOL #NDMA-2026-UK-04
        </span>
      </div>

      <details className="mx-gutter-lg my-space-sm p-space-sm rounded border border-[#d4af37]/25 font-mono text-xs" open><summary className="text-primary cursor-pointer">Actual session capacity scenario · independent of demonstration emergency panels</summary><ScenarioDetails result={lastScenario} /></details>
      {/* Scenario Header */}
      <div className="px-gutter-lg py-space-md border-b border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-space-md">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-500/50 uppercase font-bold">
              TACTICAL SCENARIO CODEX D-4
            </span>
            <span className="text-xs font-mono text-slate-400">// DISASTER MODE ACTIVATED</span>
          </div>
          <h2 className="text-xl md:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <span className="material-symbols-outlined text-[24px] text-red-500 animate-pulse">crisis_alert</span>
            <span>Kaudiyala Slope Shear &amp; Flash Flood Surge on Alaknanda River</span>
          </h2>
        </div>

        {/* Severity Badge */}
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-red-950/60 border border-red-500/60 text-red-200 text-xs font-mono flex items-center gap-2 shadow-[0_0_15px_rgba(239,68,68,0.3)]">
            <span className="material-symbols-outlined text-[16px] text-red-400">emergency</span>
            <span className="font-bold">THREAT LEVEL 3 CRITICAL</span>
          </div>
        </div>
      </div>

      {/* 4 Tactical Status Modules (KPI Tiles) */}
      <div className="px-gutter-lg py-space-sm">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-space-sm">
          
          {/* Tile 1: Stranded Pax */}
          <div className="bg-[#140e10] p-space-md rounded-xl border border-red-500/40 shadow-lg glow-red-card">
            <div className="flex justify-between items-center text-[10px] font-mono text-red-300 uppercase">
              <span>STRANDED IN-TRANSIT PAX</span>
              <span className="px-1.5 py-0.5 rounded bg-red-900/60 text-red-200 font-bold">EXPOSURE</span>
            </div>
            <div className="text-3xl font-extrabold text-white my-1 font-mono tracking-tight">
              12,400
            </div>
            <div className="flex justify-between text-xs font-mono text-red-400">
              <span>8,200 At Kaudiyala</span>
              <span>4,200 Devprayag</span>
            </div>
          </div>

          {/* Tile 2: Primary Route */}
          <div className="bg-[#140e10] p-space-md rounded-xl border border-red-500/40 shadow-lg glow-red-card">
            <div className="flex justify-between items-center text-[10px] font-mono text-red-300 uppercase">
              <span>PRIMARY ARTERY (NH-58)</span>
              <span className="px-1.5 py-0.5 rounded bg-red-900/60 text-red-200 font-bold">SEVERED</span>
            </div>
            <div className="text-2xl font-extrabold text-red-400 my-1 font-mono tracking-tight">
              NH-58 BLOCKED
            </div>
            <div className="text-xs font-mono text-slate-400">
              Km 66 Mass Rockfall Shear (400m rubble)
            </div>
          </div>

          {/* Tile 3: Evacuation Corridor */}
          <div className="bg-[#101412] p-space-md rounded-xl border border-emerald-500/40 shadow-lg">
            <div className="flex justify-between items-center text-[10px] font-mono text-emerald-300 uppercase">
              <span>EVACUATION BYPASS (TEHRI)</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold">ACTIVE</span>
            </div>
            <div className="text-3xl font-extrabold text-emerald-400 my-1 font-mono tracking-tight">
              94% CAP
            </div>
            <div className="text-xs font-mono text-slate-300">
              Flow: 650 PCU/h diverted via Chamba
            </div>
          </div>

          {/* Tile 4: Flash Flood Sensor */}
          <div className="bg-[#14120e] p-space-md rounded-xl border border-amber-500/40 shadow-lg">
            <div className="flex justify-between items-center text-[10px] font-mono text-amber-300 uppercase">
              <span>CWC HYDRO INUNDATION</span>
              <span className="px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 font-bold">PEAK STAGE</span>
            </div>
            <div className="text-3xl font-extrabold text-amber-400 my-1 font-mono tracking-tight">
              84 mm/h
            </div>
            <div className="text-xs font-mono text-slate-300">
              Alaknanda Level: +3.8m above warning mark
            </div>
          </div>

        </div>
      </div>

      {/* Main Grid: 8-Cols Emergency Tactical Vector Map + 4-Cols Tactical Operations Matrix */}
      <div className="px-gutter-lg pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md">
          
          {/* Left: 8-Column Emergency Tactical Map Display */}
          <div className="lg:col-span-8 flex flex-col bg-[#070507] rounded-xl border border-red-500/35 overflow-hidden shadow-2xl relative">
            
            {/* Map Console Bar */}
            <div className="p-space-sm bg-[#120a0d] border-b border-red-500/20 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-red-500">map</span>
                <span className="text-xs font-bold text-red-200 uppercase font-mono">
                  CRISIS MAP // VECTOR OVERLAY &amp; INUNDATION GRADIENT
                </span>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                <span className="flex items-center gap-1 text-red-400">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
                  BLOCKADE: KM 66
                </span>
                <span>|</span>
                <span className="text-emerald-400 font-bold">EVAC ROUTE 2 LIVE</span>
              </div>
            </div>

            {/* Emergency Vector Map Canvas */}
            <div className="relative w-full h-[480px] subtle-grid overflow-hidden bg-[#070407]">
              <svg 
                className="absolute inset-0 w-full h-full select-none" 
                viewBox="0 0 960 520" 
                preserveAspectRatio="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <linearGradient id="inundationGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.4" />
                    <stop offset="50%" stopColor="#7f1d1d" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#080709" stopOpacity="0.9" />
                  </linearGradient>

                  <pattern id="blockedHatch" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                    <line x1="0" y1="0" x2="0" y2="10" stroke="#ef4444" strokeWidth="2.5" />
                  </pattern>
                </defs>

                {/* River Flash Flood Basin in Crimson / Amber */}
                <path
                  d="M 120 480 Q 280 410 440 330 T 640 220 T 880 140"
                  fill="none"
                  stroke="url(#inundationGradient)"
                  strokeWidth="48"
                  strokeLinecap="round"
                />

                {/* Severed Section of Highway NH-58 */}
                <path
                  d="M 160 440 Q 280 370 420 310"
                  fill="none"
                  stroke="#f2ca50"
                  strokeWidth="5"
                  strokeLinecap="round"
                />

                {/* Blocked Zone (Red Hatched) */}
                <path
                  d="M 420 310 L 520 270"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="8"
                  strokeDasharray="6 4"
                />

                {/* Remaining Highway after blockade */}
                <path
                  d="M 520 270 Q 660 210 820 150"
                  fill="none"
                  stroke="#f2ca50"
                  strokeWidth="5"
                  opacity="0.4"
                />

                {/* Active Alternate Tehri Evacuation Bypass Corridor (Emerald Green) */}
                <path
                  d="M 160 440 Q 220 280 390 190 T 680 180 T 820 150"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="4"
                  strokeDasharray="6 3"
                />

                {/* Blockade Rupture Polygon */}
                <polygon points="410,290 530,250 540,290 420,330" fill="rgba(239, 68, 68, 0.45)" stroke="#ef4444" strokeWidth="1.5" />

                {/* Blockade Label */}
                <g transform="translate(470, 240)">
                  <rect x="-85" y="-14" width="170" height="24" rx="3" fill="#450a0a" stroke="#ef4444" strokeWidth="1" />
                  <text x="0" y="2" fill="#ffb4ab" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle" fontWeight="bold">
                    KAUDIYALA SLOPE SHEAR
                  </text>
                </g>

                {/* Helipad Extraction Nodes */}
                <g transform="translate(260, 240)">
                  <circle cx="0" cy="0" r="16" fill="rgba(16, 185, 129, 0.2)" stroke="#10b981" strokeWidth="1.5" strokeDasharray="3 2" />
                  <text x="0" y="4" fill="#10b981" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle" fontWeight="bold">H-1</text>
                  <text x="0" y="20" fill="#a7f3d0" fontSize="8" fontFamily="JetBrains Mono" textAnchor="middle">AIRLIFT STAGING</text>
                </g>

                <g transform="translate(680, 140)">
                  <circle cx="0" cy="0" r="16" fill="rgba(16, 185, 129, 0.2)" stroke="#10b981" strokeWidth="1.5" strokeDasharray="3 2" />
                  <text x="0" y="4" fill="#10b981" fontSize="10" fontFamily="JetBrains Mono" textAnchor="middle" fontWeight="bold">H-2</text>
                  <text x="0" y="20" fill="#a7f3d0" fontSize="8" fontFamily="JetBrains Mono" textAnchor="middle">DEVPRAYAG HELI</text>
                </g>

                {/* Evacuation flow animation */}
                <circle cx="390" cy="190" r="4" fill="#10b981">
                  <animate attributeName="opacity" values="0.3;1;0.3" dur="1s" repeatCount="indefinite" />
                </circle>
              </svg>

              {/* In-Map Telemetry Hud */}
              <div className="absolute bottom-4 left-4 z-20 bg-[#160c10]/90 border border-red-500/40 rounded-lg p-3 max-w-sm backdrop-blur-md font-mono text-xs text-slate-300">
                <div className="text-red-400 font-bold mb-1 flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">warning</span>
                  <span>COLLAPSE ANALYSIS // KM 66.4</span>
                </div>
                <div className="text-[11px] text-slate-300 leading-tight">
                  Estimated 28,000 m³ fractured quartzite debris on dual roadway. Heavy hydraulic earthmovers dispatched from Rishikesh depot. Estimated clearance time: 14.5 hours.
                </div>
              </div>
            </div>

            {/* Map Status Bar */}
            <div className="p-space-sm bg-[#120a0d] border-t border-red-500/20 flex flex-wrap items-center justify-between text-xs font-mono text-slate-400">
              <span className="text-red-300 font-semibold">INCIDENT COMMAND SYSTEM LEVEL-3 AUTHORIZED</span>
              <button
                type="button"
                onClick={() => onNavigate('overview')}
                className="text-primary hover:underline flex items-center gap-1"
              >
                <span>Back to Overview Dashboard</span>
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
              </button>
            </div>

          </div>

          {/* Right: 4-Column Tactical Operations Matrix */}
          <div className="lg:col-span-4 flex flex-col gap-space-md">
            
            {/* Pre-Positioned Assets */}
            <div className="bg-[#120b0e] rounded-xl border border-white/10 p-space-md shadow-xl flex flex-col gap-2.5">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs font-bold">
                  PRE-POSITIONED ASSETS
                </span>
                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-950 px-1.5 py-0.5 rounded">
                  4 DEPLOYED
                </span>
              </div>

              <div className="flex flex-col gap-2 text-xs font-mono">
                <div className="p-2 rounded bg-surface-container border border-white/5 flex items-center justify-between">
                  <div>
                    <div className="text-white font-bold">NDRF 8th Battalion</div>
                    <div className="text-[10px] text-slate-400">120 Rescuers • 4 Earthmovers</div>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold">
                    AT SITE
                  </span>
                </div>

                <div className="p-2 rounded bg-surface-container border border-white/5 flex items-center justify-between">
                  <div>
                    <div className="text-white font-bold">SDRF Quick Response Unit</div>
                    <div className="text-[10px] text-slate-400">Devprayag • 8 Watercraft</div>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 font-bold">
                    DEPLOYED
                  </span>
                </div>

                <div className="p-2 rounded bg-surface-container border border-white/5 flex items-center justify-between">
                  <div>
                    <div className="text-white font-bold">Medical Airlift (MI-17)</div>
                    <div className="text-[10px] text-slate-400">Jolly Grant Tarmac • 2 Units</div>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 font-bold">
                    STANDBY
                  </span>
                </div>

                <div className="p-2 rounded bg-surface-container border border-white/5 flex items-center justify-between">
                  <div>
                    <div className="text-white font-bold">Rishikesh Relief Camp</div>
                    <div className="text-[10px] text-slate-400">Capacity: 4,200 pax warm beds</div>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-primary/20 text-primary font-bold">
                    READY
                  </span>
                </div>
              </div>
            </div>

            {/* Candidate Civil Actions Checklist */}
            <div className="bg-[#120b0e] rounded-xl border border-red-500/35 p-space-md shadow-xl flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="font-label-caps text-label-caps text-red-200 uppercase tracking-wider text-xs font-bold">
                  CANDIDATE CIVIL ACTIONS
                </span>
                <span className="text-[9px] font-mono text-primary">
                  {authorizedCount} SELECTED
                </span>
              </div>

              <div className="flex flex-col gap-2.5">
                {[
                  { key: 'haltIngress', label: 'Halt Ingress at Tapovan Checkpoint', sub: 'Stop mountain-bound vehicles at Rishikesh gateway.' },
                  { key: 'tehriBypass', label: 'Activate Tehri Bypass Diversion', sub: 'Direct all light transit via Chamba-New Tehri road.' },
                  { key: 'smsBroadcast', label: 'Broadcast Geo-Fenced Tier-3 SMS', sub: 'Alert all mobile handsets in 25km radius in Hindi/English.' },
                  { key: 'heliEvac', label: 'Authorize Helicopter Evacuation', sub: 'Scramble MI-17 for stranded high-altitude pilgrims.' },
                  { key: 'powerIsolate', label: 'Isolate High-Voltage Substation 04', sub: 'Prevent electrical fires near riverbank inundation zone.' },
                ].map(({ key, label, sub }) => (
                  <label
                    key={key}
                    onClick={() => toggleAction(key)}
                    className="p-2 rounded bg-surface-container-high border border-white/5 hover:border-white/20 transition-all flex items-start gap-2.5 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={actions[key]}
                      onChange={() => {}}
                      className="mt-0.5 accent-primary w-4 h-4 rounded cursor-pointer"
                    />
                    <div className="flex flex-col">
                      <span className="text-xs font-bold text-white leading-tight">{label}</span>
                      <span className="text-[10px] text-slate-400">{sub}</span>
                    </div>
                  </label>
                ))}
              </div>

              {/* Authorize Action Button */}
              <button
                type="button"
                onClick={handleAuthorizeBrief}
                className="w-full mt-2 py-3 rounded-lg bg-gradient-to-r from-red-600 via-amber-600 to-red-600 hover:from-red-500 hover:to-amber-500 text-white font-bold text-xs uppercase font-mono tracking-wider shadow-lg glow-red-card transition-all"
              >
                Authorize Protocol Brief ({authorizedCount})
              </button>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
