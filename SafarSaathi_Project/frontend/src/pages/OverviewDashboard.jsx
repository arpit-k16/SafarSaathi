import React, { useState } from 'react';
import { useApiQuery } from '../hooks/useApi.js';
import { overviewData } from '../services/api/resources.js';
import { number } from '../services/api/adapters.js';
import ApiState from '../components/ApiState.jsx';

const WAYPOINTS = [
  { id: 'tapovan', name: 'Tapovan Pedestrian Core', km: 'Km 00', status: 'CROWD SURGE', pcu: '1,120 PCU/h', stress: 84, rain: '12 mm/h', coords: { x: 180, y: 390 } },
  { id: 'kaudiyala', name: 'Kaudiyala Slump Zone', km: 'Km 66', status: 'ROCKFALL DANGER', pcu: '480 PCU/h', stress: 92, rain: '42 mm/h', isAlert: true, coords: { x: 380, y: 270 } },
  { id: 'devprayag', name: 'Devprayag Confluence', km: 'Km 72', status: 'MODERATE FLOW', pcu: '820 PCU/h', stress: 62, rain: '24 mm/h', coords: { x: 510, y: 220 } },
  { id: 'srinagar', name: 'Srinagar Hydropower Basin', km: 'Km 105', status: 'MONITORED', pcu: '750 PCU/h', stress: 54, rain: '18 mm/h', coords: { x: 640, y: 170 } },
  { id: 'rudraprayag', name: 'Rudraprayag Junction', km: 'Km 140', status: 'NOMINAL TRANSIT', pcu: '610 PCU/h', stress: 48, rain: '15 mm/h', coords: { x: 740, y: 110 } },
];

export default function OverviewDashboard({ onNavigate, showToast }) {
  const [selectedWaypoint, setSelectedWaypoint] = useState(WAYPOINTS[1]); // Kaudiyala by default
  const [activeLayer, setActiveLayer] = useState('roads'); // 'roads' | 'insar' | 'sensors' | 'evac'
  const query = useApiQuery('overview', overviewData);
  const annual = query.data?.history.data?.series.find(r => r.frequency === 'annual')?.observations.at(-1);
  const monthly = query.data?.history.data?.series.find(r => r.frequency === 'monthly')?.observations.at(-1);
  const sourceErrors = Object.entries(query.data || {}).filter(([, value]) => value.error);
  const metric = (value, compact = false) => query.loading ? 'Loading…'
    : typeof value !== 'number' ? 'UNAVAILABLE'
    : compact ? new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 2 }).format(value) : number(value);
  const monthlyRows = query.data?.history.data?.series.find(r => r.frequency === 'monthly')?.observations || [];
  const chartRows = monthlyRows.slice(-12);
  const chartMax = Math.max(1, ...chartRows.map(r => r.arrivals));
  const chartPath = chartRows.map((r, i) => `${i ? 'L' : 'M'} ${i / Math.max(1, chartRows.length - 1) * 300} ${76 - r.arrivals / chartMax * 70}`).join(' ');
  const [dispatchModal, setDispatchModal] = useState(null);

  const handleTriggerAction = (actionTitle, actionDesc) => {
    setDispatchModal({
      title: actionTitle,
      description: actionDesc,
    });
  };

  const handleConfirmDispatch = () => {
    if (dispatchModal) {
      showToast({
        title: 'Demo action only — no dispatch',
        message: `${dispatchModal.title}: no regional units, SMS or audit service is connected.`,
        type: 'success',
      });
      setDispatchModal(null);
    }
  };

  return (
    <div data-page="overview" className="flex flex-col w-full bg-surface text-on-surface">
      {/* Sub-header Command Strip */}
      <div className="px-gutter-lg pt-space-md pb-space-sm flex flex-col md:flex-row md:items-center justify-between gap-space-sm border-b border-white/5">
        <div className="flex items-center gap-space-sm flex-wrap">
          <div className="flex items-center gap-space-xs px-2 py-0.5 rounded bg-surface-container-high text-primary font-telemetry-sm text-telemetry-sm tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
            <span>SECTOR: 07-GARHWAL</span>
          </div>
          <span className="text-on-surface-variant font-telemetry-sm text-telemetry-sm tracking-widest text-xs">
            // BACKEND SUMMARY + DEMO SCHEMATIC
          </span>
          <div className="hidden sm:flex items-center gap-1 text-on-surface-variant font-telemetry-sm text-telemetry-sm text-xs">
            <span className="text-primary font-semibold">GRID:</span> 30.0869° N, 78.2676° E
          </div>
        </div>

        <div className="flex items-center gap-space-sm">
          <div className="px-2 py-0.5 rounded bg-surface-container-low text-secondary font-telemetry-sm text-telemetry-sm flex items-center gap-1 shadow-sm border border-secondary/20">
            <span className="material-symbols-outlined text-[14px]">science</span>
            <span>HISTORICAL DATA • SCHEMATIC SECTIONS: DEMO DATA</span>
          </div>
          <div className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant font-telemetry-sm text-telemetry-sm text-xs">
            ON-DEMAND API
          </div>
        </div>
      </div>

      <div className="px-gutter-lg"><ApiState {...query} />{sourceErrors.map(([name, value]) => <p role="alert" key={name} className="font-mono text-xs text-amber-400">{name}: {value.error}</p>)}</div>
      {/* Top 5 KPI Cards */}
      <div className="px-gutter-lg py-space-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-space-sm">
          
          {/* KPI 1: Tourist Load */}
          <div className="relative bg-surface-container-low p-space-md rounded shadow-md border border-[#d4af37]/20 overflow-hidden group hover:bg-surface-container transition-all">
            <div className="flex items-center justify-between mb-space-xs">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-[10px]">
                ANNUAL ARRIVALS
              </span>
              <span className="px-1.5 py-0.5 rounded bg-surface-container-highest text-primary font-telemetry-sm text-telemetry-sm text-[9px]">
                HISTORICAL
              </span>
            </div>
            <div className="flex items-baseline gap-space-xs my-1">
              <span className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight text-2xl">
                {metric(annual?.arrivals, true)}
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant text-xs">{annual?.year ?? '—'} · IND</span>
            </div>
            <div className="flex items-center justify-between text-body-sm font-body-sm mt-space-xs text-on-surface-variant text-xs">
              <span className="flex items-center gap-0.5 text-primary font-telemetry-sm text-telemetry-sm">
                <span className="material-symbols-outlined text-[14px]">trending_up</span> NATIONAL TOTAL
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant tracking-wider">WORLD BANK</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded mt-space-xs overflow-hidden">
              <div className="bg-primary h-full rounded transition-all duration-500 shadow-[0_0_8px_#f2ca50]" style={{ width: '0%' }}></div>
            </div>
          </div>

          {/* KPI 2: Destination Stress Index */}
          <div className="relative bg-surface-container-low p-space-md rounded shadow-md border border-[#ee9800]/25 overflow-hidden group hover:bg-surface-container transition-all">
            <div className="flex items-center justify-between mb-space-xs">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-[10px]">
                SOURCE LOCATIONS
              </span>
              <span className="px-1.5 py-0.5 rounded bg-secondary-container/20 text-secondary font-telemetry-sm text-telemetry-sm text-[9px] font-bold">
                STATIC
              </span>
            </div>
            <div className="flex items-baseline gap-space-xs my-1">
              <span className="font-headline-lg text-headline-lg text-secondary font-semibold tracking-tight text-2xl">
                {metric(query.data?.destinations.data?.destinations.length)}
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant text-xs">grid points</span>
            </div>
            <div className="flex items-center justify-between text-body-sm font-body-sm mt-space-xs text-on-surface-variant text-xs">
              <span className="flex items-center gap-0.5 text-secondary font-telemetry-sm text-telemetry-sm">
                <span className="material-symbols-outlined text-[14px]">warning</span> NASA POWER
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-secondary tracking-wider">ARCHIVED</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded mt-space-xs overflow-hidden">
              <div className="bg-secondary h-full rounded transition-all duration-500 shadow-[0_0_8px_#ffb95f]" style={{ width: '0%' }}></div>
            </div>
          </div>

          {/* KPI 3: Hazard Exposure */}
          <div className="relative bg-surface-container-low p-space-md rounded shadow-md border border-error/30 overflow-hidden group hover:bg-surface-container transition-all">
            <div className="flex items-center justify-between mb-space-xs">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-[10px]">
                LOCAL DATA FILES
              </span>
              <span className="px-1.5 py-0.5 rounded bg-error/20 text-error font-telemetry-sm text-telemetry-sm text-[9px] font-bold">
                INVENTORY
              </span>
            </div>
            <div className="flex items-baseline gap-space-xs my-1">
              <span className="font-headline-lg text-headline-lg text-error font-semibold tracking-tight text-2xl">
                {metric(query.data?.datasets.data?.total)}
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant text-xs">FILES</span>
            </div>
            <div className="flex items-center justify-between text-body-sm font-body-sm mt-space-xs text-on-surface-variant text-xs">
              <span className="flex items-center gap-0.5 text-error font-telemetry-sm text-telemetry-sm">
                <span className="material-symbols-outlined text-[14px]">landslide</span> FILE STATS ONLY
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-error tracking-wider">NOT RECORD COUNTS</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded mt-space-xs overflow-hidden">
              <div className="bg-error h-full rounded transition-all duration-500 shadow-[0_0_8px_#ffb4ab]" style={{ width: '0%' }}></div>
            </div>
          </div>

          {/* KPI 4: Route Congestion */}
          <div className="relative bg-surface-container-low p-space-md rounded shadow-md border border-[#d4af37]/20 overflow-hidden group hover:bg-surface-container transition-all">
            <div className="flex items-center justify-between mb-space-xs">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-[10px]">
                MODEL ARTIFACTS
              </span>
              <span className="px-1.5 py-0.5 rounded bg-surface-container-highest text-primary font-telemetry-sm text-telemetry-sm text-[9px]">
                REGISTRY
              </span>
            </div>
            <div className="flex items-baseline gap-space-xs my-1">
              <span className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight text-2xl">
                {metric(query.data?.models.data?.length)}
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant text-xs">REGISTERED</span>
            </div>
            <div className="flex items-center justify-between text-body-sm font-body-sm mt-space-xs text-on-surface-variant text-xs">
              <span className="flex items-center gap-0.5 text-primary font-telemetry-sm text-telemetry-sm">
                <span className="material-symbols-outlined text-[14px]">traffic</span> PERSISTED PIPELINES
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant tracking-wider">EXPERIMENTAL</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded mt-space-xs overflow-hidden">
              <div className="bg-primary/80 h-full rounded transition-all duration-500" style={{ width: '0%' }}></div>
            </div>
          </div>

          {/* KPI 5: Environmental Vulnerability */}
          <div className="relative bg-surface-container-low p-space-md rounded shadow-md border border-[#d4af37]/20 overflow-hidden group hover:bg-surface-container transition-all">
            <div className="flex items-center justify-between mb-space-xs">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-[10px]">
                LATEST MONTHLY FTA
              </span>
              <span className="px-1.5 py-0.5 rounded bg-surface-container-highest text-on-surface-variant font-telemetry-sm text-telemetry-sm text-[9px]">
                HISTORICAL
              </span>
            </div>
            <div className="flex items-baseline gap-space-xs my-1">
              <span className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight text-2xl">
                {metric(monthly?.arrivals, true)}
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant text-xs">{monthly?.date ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between text-body-sm font-body-sm mt-space-xs text-on-surface-variant text-xs">
              <span className="flex items-center gap-0.5 text-primary font-telemetry-sm text-telemetry-sm">
                <span className="material-symbols-outlined text-[14px]">water_drop</span> IND · EXCLUDES NRI
              </span>
              <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant tracking-wider">MINISTRY OF TOURISM</span>
            </div>
            <div className="w-full bg-surface-container-highest h-1 rounded mt-space-xs overflow-hidden">
              <div className="bg-primary/60 h-full rounded transition-all duration-500" style={{ width: '0%' }}></div>
            </div>
          </div>

        </div>
      </div>

      {/* Main Command Grid: 8-Col Vector Map + 4-Col Intelligence Drawer */}
      <div className="px-gutter-lg pb-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md">
          
          {/* Left: 8-Column Tactical Geospatial Map */}
          <div className="lg:col-span-8 flex flex-col bg-surface-container-lowest rounded-xl border border-[#d4af37]/20 overflow-hidden shadow-2xl relative">
            
            {/* Map Top Bar */}
            <div className="p-space-sm bg-surface-container-low border-b border-white/5 flex flex-wrap items-center justify-between gap-space-xs">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-primary">layers</span>
                <span className="font-label-caps text-label-caps text-on-surface uppercase tracking-wider text-xs font-bold">
                  NH-58 ARTERIAL // RISHIKESH - DEVPRAYAG CORRIDOR
                </span>
                <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-mono text-[9px] border border-primary/30">
                  DEMO SCHEMATIC
                </span>
              </div>

              {/* Layer Toggles */}
              <div className="flex items-center gap-1 font-mono text-[10px]">
                {[
                  { id: 'roads', label: 'Roads & Flow' },
                  { id: 'insar', label: 'InSAR Slips' },
                  { id: 'sensors', label: 'IoT Stations' },
                  { id: 'evac', label: 'Evac Routes' },
                ].map((layer) => (
                  <button
                    key={layer.id}
                    type="button"
                    onClick={() => setActiveLayer(layer.id)}
                    className={`px-2 py-1 rounded transition-colors ${
                      activeLayer === layer.id
                        ? 'bg-primary text-on-primary font-bold shadow-[0_0_10px_rgba(212,175,55,0.3)]'
                        : 'bg-surface-container text-slate-400 hover:text-white'
                    }`}
                  >
                    {layer.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tactical SVG Map Canvas */}
            <div className="relative w-full h-[480px] bg-[#07090e] subtle-grid overflow-hidden">
              
              {/* Raster Scanning Line Animation */}
              <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-[#d4af37]/40 to-transparent pointer-events-none animate-scanline z-20"></div>

              {/* Vector SVG Artery Display */}
              <svg 
                className="absolute inset-0 w-full h-full" 
                preserveAspectRatio="none" 
                viewBox="0 0 800 520" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <linearGradient id="gangaRiverGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#0284c7" stopOpacity="0.4" />
                    <stop offset="50%" stopColor="#0369a1" stopOpacity="0.6" />
                    <stop offset="100%" stopColor="#082f49" stopOpacity="0.3" />
                  </linearGradient>

                  <linearGradient id="nh58Flow" x1="0%" y1="100%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#f2ca50" />
                    <stop offset="50%" stopColor="#ffb95f" />
                    <stop offset="100%" stopColor="#d4af37" />
                  </linearGradient>

                  <radialGradient id="alertPipGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.9" />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
                  </radialGradient>
                </defs>

                {/* River Ganga winding path */}
                <path
                  d="M 120 480 Q 220 430 300 370 T 450 280 T 600 200 T 780 130"
                  fill="none"
                  stroke="url(#gangaRiverGrad)"
                  strokeWidth="24"
                  strokeLinecap="round"
                  opacity="0.8"
                />

                {/* River Centerline */}
                <path
                  d="M 120 480 Q 220 430 300 370 T 450 280 T 600 200 T 780 130"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="2"
                  strokeDasharray="6 4"
                  opacity="0.6"
                />

                {/* Alternate Tehri Bypass Road (Green / Secondary) */}
                {(activeLayer === 'roads' || activeLayer === 'evac') && (
                  <path
                    d="M 180 390 Q 280 280 430 200 T 640 170"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="3"
                    strokeDasharray="4 3"
                    opacity="0.7"
                  />
                )}

                {/* Primary NH-58 Highway Artery */}
                <path
                  d="M 180 390 Q 270 330 380 270 T 510 220 T 640 170 T 740 110"
                  fill="none"
                  stroke="url(#nh58Flow)"
                  strokeWidth="5"
                  strokeLinecap="round"
                />

                {/* InSAR Slips Layer Markers */}
                {activeLayer === 'insar' && (
                  <g>
                    <polygon points="360,250 400,240 420,285 370,295" fill="rgba(239, 68, 68, 0.3)" stroke="#ef4444" strokeWidth="1.5" strokeDasharray="3 2" />
                    <text x="350" y="235" fill="#ffb4ab" fontSize="9" fontFamily="JetBrains Mono">ZONE SLIP 0.24mm/d</text>
                  </g>
                )}

                {/* Flow vectors animation */}
                <circle cx="280" cy="330" r="3" fill="#f2ca50">
                  <animate attributeName="opacity" values="0.2;1;0.2" dur="1.5s" repeatCount="indefinite" />
                </circle>
                <circle cx="580" cy="190" r="3" fill="#f2ca50">
                  <animate attributeName="opacity" values="0.2;1;0.2" dur="1.5s" repeatCount="indefinite" />
                </circle>
              </svg>

              {/* Waypoint Interactive Marker Nodes */}
              {WAYPOINTS.map((wp) => {
                const isSelected = selectedWaypoint.id === wp.id;
                return (
                  <div
                    key={wp.id}
                    onClick={() => setSelectedWaypoint(wp)}
                    style={{ left: `${wp.coords.x}px`, top: `${wp.coords.y}px` }}
                    className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer z-30 group"
                  >
                    {/* Pulsing ring */}
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-all ${
                      isSelected
                        ? 'bg-primary/20 border-2 border-primary shadow-[0_0_15px_#f2ca50]'
                        : wp.isAlert
                        ? 'bg-red-500/20 border-2 border-red-500 shadow-[0_0_15px_#ef4444]'
                        : 'bg-surface-container border border-white/20 group-hover:border-primary'
                    }`}>
                      <div className={`w-2.5 h-2.5 rounded-full ${
                        wp.isAlert ? 'bg-red-500 animate-ping' : isSelected ? 'bg-primary' : 'bg-slate-300'
                      }`}></div>
                    </div>

                    {/* Node Tooltip Label */}
                    <div className={`absolute top-full left-1/2 -translate-x-1/2 mt-1 px-2 py-0.5 rounded text-[10px] font-mono whitespace-nowrap pointer-events-none transition-all ${
                      isSelected
                        ? 'bg-[#12151e] text-primary border border-primary/50 font-bold shadow-lg'
                        : 'bg-surface-container-highest/90 text-slate-300 border border-white/10 group-hover:text-white'
                    }`}>
                      {wp.name} ({wp.km})
                    </div>
                  </div>
                );
              })}

              {/* Selected Waypoint Telemetry Overlay Card */}
              {selectedWaypoint && (
                <div className="absolute bottom-4 left-4 z-40 bg-[#0d1117]/95 border border-[#d4af37]/40 rounded-lg p-3 max-w-xs shadow-2xl backdrop-blur-md">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-slate-400">
                      WAYPOINT INSPECTION // {selectedWaypoint.km}
                    </span>
                    <span className={`px-1.5 py-0.2 rounded font-mono text-[8px] font-bold ${
                      selectedWaypoint.isAlert ? 'bg-red-950 text-red-400 border border-red-500/40' : 'bg-primary/10 text-primary'
                    }`}>
                      {selectedWaypoint.status}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-white mb-2">{selectedWaypoint.name}</div>
                  <div className="grid grid-cols-3 gap-2 text-center font-mono text-[10px]">
                    <div className="bg-surface-container p-1 rounded">
                      <div className="text-slate-400 text-[8px]">THROUGHPUT</div>
                      <div className="text-primary font-bold">{selectedWaypoint.pcu}</div>
                    </div>
                    <div className="bg-surface-container p-1 rounded">
                      <div className="text-slate-400 text-[8px]">STRESS</div>
                      <div className={`font-bold ${selectedWaypoint.stress > 80 ? 'text-red-400' : 'text-amber-400'}`}>
                        {selectedWaypoint.stress}/100
                      </div>
                    </div>
                    <div className="bg-surface-container p-1 rounded">
                      <div className="text-slate-400 text-[8px]">RAIN GAUGE</div>
                      <div className="text-slate-200 font-bold">{selectedWaypoint.rain}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Compass HUD */}
              <div className="absolute top-4 right-4 z-30 font-mono text-[9px] text-slate-400 bg-surface-container-lowest/80 px-2 py-1 rounded border border-white/10 flex items-center gap-1">
                <span className="text-primary font-bold">▲ N</span>
                <span>AZI: 042° // ELEV: 1,240m</span>
              </div>
            </div>

            {/* Map Footer Status Bar */}
            <div className="p-space-sm bg-surface-container-low border-t border-white/5 flex flex-wrap items-center justify-between text-xs font-mono text-slate-400">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-primary"></span>
                  <span>NH-58 Open</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  <span>Kaudiyala Slump Restriced</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span>Tehri Alternate Active</span>
                </span>
              </div>
              <button
                type="button"
                onClick={() => onNavigate('destination-twin')}
                className="text-primary hover:underline flex items-center gap-1"
              >
                <span>Launch 3D Digital Twin</span>
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
              </button>
            </div>

          </div>

          {/* Right: 4-Column Intelligence & Intervention Drawer */}
          <div className="lg:col-span-4 flex flex-col gap-space-md">
            
            {/* Active Bottlenecks & Critical Warnings */}
            <div className="bg-surface-container-lowest rounded-xl border border-red-500/30 p-space-md shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-1.5 text-error font-label-caps text-label-caps text-xs font-bold uppercase tracking-wider">
                  <span className="material-symbols-outlined text-[18px]">warning</span>
                  <span>DEMO CHOKEPOINTS</span>
                </div>
                <span className="px-1.5 py-0.5 rounded bg-red-950/60 text-red-400 font-mono text-[9px] border border-red-500/40">
                  DEMO DATA
                </span>
              </div>

              <div className="flex flex-col gap-2.5">
                {/* Chokepoint 1 */}
                <div className="p-2.5 rounded bg-[#161214] border border-red-500/30 flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-red-200">Kaudiyala Km 66 Rockfall</span>
                    <span className="text-[10px] font-mono text-red-400 font-semibold">1-LANE CHOKE</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Precipitation threshold exceeded (42mm/h). InSAR indicates 0.24mm shear. Traffic throughput curtailed to 480 PCU/h.
                  </p>
                  <div className="mt-1 flex items-center justify-between pt-1 border-t border-white/5">
                    <span className="text-[9px] font-mono text-slate-500">REC: MICRO-METERING</span>
                    <button
                      type="button"
                      onClick={() => handleTriggerAction('Micro-Metering at Tapovan', 'Limit upstream ingress to 350 vehicles/hour to prevent mountain gridlock.')}
                      className="px-2 py-0.5 rounded bg-primary/20 text-primary border border-primary/40 hover:bg-primary/30 text-[10px] font-mono font-bold transition-colors"
                    >
                      Deploy Metering
                    </button>
                  </div>
                </div>

                {/* Chokepoint 2 */}
                <div className="p-2.5 rounded bg-[#1a1712] border border-amber-500/30 flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-200">Tapovan Pedestrian Surge</span>
                    <span className="text-[10px] font-mono text-amber-400 font-semibold">3.2 PAX/M²</span>
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Laxman Jhula pedestrian approach nearing stampede risk density. Ingress flow exceeds carrying capacity by 34%.
                  </p>
                  <div className="mt-1 flex items-center justify-between pt-1 border-t border-white/5">
                    <span className="text-[9px] font-mono text-slate-500">REC: CELL BROADCAST</span>
                    <button
                      type="button"
                      onClick={() => handleTriggerAction('Geo-Fenced Tourist Advisory', 'Transmit cell broadcast advisory redirecting foot traffic to Ram Jhula promenade.')}
                      className="px-2 py-0.5 rounded bg-secondary/20 text-secondary border border-secondary/40 hover:bg-secondary/30 text-[10px] font-mono font-bold transition-colors"
                    >
                      Broadcast SMS
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Carrying-Capacity Predictive Curve Chart */}
            <div className="bg-surface-container-lowest rounded-xl border border-[#d4af37]/20 p-space-md shadow-xl flex flex-col justify-between">
              <div className="flex items-center justify-between mb-2">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs">
                  HISTORICAL MONTHLY FTA · INDIA
                </span>
                <span className="font-mono text-[9px] text-primary">{monthly?.date ?? 'DATA UNAVAILABLE'}</span>
              </div>

              {/* Chart SVG */}
              <div className="w-full h-32 bg-[#0c0e14] rounded border border-white/5 p-2 relative flex flex-col justify-between">
                <div className="absolute top-3 left-2 right-2 border-b border-red-500/40 border-dashed z-10 flex justify-end">
                  <span className="text-[8px] font-mono text-red-400 bg-[#0c0e14] px-1 -mt-2">HISTORICAL COUNTS · NO CAPACITY THRESHOLD</span>
                </div>
                
                <svg className="w-full h-full" viewBox="0 0 300 80" preserveAspectRatio="none">
                  {/* Fill gradient */}
                  <defs>
                    <linearGradient id="curveFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#f2ca50" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#f2ca50" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  
                  {/* Area fill */}
                  <path
                    d={chartPath ? `${chartPath} L 300 80 L 0 80 Z` : ''}
                    fill="url(#curveFill)"
                  />
                  
                  {/* Curve Line */}
                  <path
                    d={chartPath}
                    fill="none"
                    stroke="#f2ca50"
                    strokeWidth="2.5"
                  />

                  {/* Current timestamp point */}
                  {chartRows.length > 0 && <circle cx="300" cy={76 - chartRows.at(-1).arrivals / chartMax * 70} r="4" fill="#ffd700" className="animate-pulse" />}
                </svg>

                <div className="flex justify-between font-mono text-[8px] text-slate-500 border-t border-white/5 pt-1">
                  <span>{chartRows[0]?.date ?? '—'}</span>
                  <span>{chartRows[3]?.date ?? '—'}</span>
                  <span className="text-primary font-bold">{chartRows[6]?.date ?? '—'}</span>
                  <span>{chartRows[9]?.date ?? '—'}</span>
                  <span>{chartRows.at(-1)?.date ?? '—'}</span>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between text-xs font-mono">
                <span className="text-slate-400">Historical units:</span>
                <span className="text-amber-400 font-bold">arrivals/month · no local capacity model</span>
              </div>
            </div>

            {/* Quick Actions Panel */}
            <div className="bg-surface-container-lowest rounded-xl border border-[#d4af37]/20 p-space-md shadow-xl">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs block mb-3">
                DEMO ACTIONS · NO DISPATCH
              </span>

              <div className="grid grid-cols-2 gap-2 font-mono text-xs">
                <button
                  type="button"
                  onClick={() => onNavigate('what-if-simulator')}
                  className="p-2.5 rounded bg-surface-container-high hover:bg-surface-container border border-white/10 hover:border-primary text-slate-200 hover:text-primary transition-all flex flex-col gap-1 text-left"
                >
                  <span className="material-symbols-outlined text-[18px] text-primary">tune</span>
                  <span className="font-bold">What-If Sim</span>
                  <span className="text-[9px] text-slate-400">Model +30% Pax / Rain</span>
                </button>

                <button
                  type="button"
                  onClick={() => onNavigate('disaster-mode')}
                  className="p-2.5 rounded bg-red-950/40 hover:bg-red-900/50 border border-red-500/40 text-red-200 hover:text-white transition-all flex flex-col gap-1 text-left shadow-[0_0_12px_rgba(239,68,68,0.2)]"
                >
                  <span className="material-symbols-outlined text-[18px] text-red-400">crisis_alert</span>
                  <span className="font-bold">Disaster Deck</span>
                  <span className="text-[9px] text-red-300">Escalate Protocol D-4</span>
                </button>
              </div>
            </div>

          </div>

        </div>
      </div>

      {/* Dispatch Action Modal */}
      {dispatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-[#0d1117] border border-[#d4af37]/50 rounded-xl p-6 shadow-2xl glow-gold-card">
            <div className="flex items-center gap-2 text-primary mb-3">
              <span className="material-symbols-outlined text-[24px]">verified_user</span>
              <h3 className="font-headline-sm text-lg font-bold">Authorize Tactical Action</h3>
            </div>
            <p className="text-sm font-semibold text-white mb-1">{dispatchModal.title}</p>
            <p className="text-xs text-slate-300 mb-6 leading-relaxed">{dispatchModal.description}</p>
            <div className="p-3 bg-surface-container rounded mb-6 font-mono text-[10px] text-slate-400 border border-white/5">
              <div>AUTHORITY: CSIR-NDMA COMMAND TIER-1</div>
              <div>GEOLOC: GARHWAL ARC SECTOR 07</div>
              <div>SECURITY PROTOCOL: SHA-256 SIGNED</div>
            </div>
            <div className="flex justify-end gap-3 font-mono text-xs">
              <button
                type="button"
                onClick={() => setDispatchModal(null)}
                className="px-4 py-2 rounded bg-surface-container text-slate-300 hover:text-white transition-colors"
              >
                Abort
              </button>
              <button
                type="button"
                onClick={handleConfirmDispatch}
                className="px-5 py-2 rounded bg-primary text-on-primary font-bold hover:bg-[#ffe088] transition-colors shadow-lg"
              >
                Authorize &amp; Transmit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
