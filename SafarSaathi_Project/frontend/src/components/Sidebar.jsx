import React from 'react';

const navGroups = [
  {
    title: 'OBSERVATION',
    items: [
      { id: 'overview', label: 'Overview', icon: 'dashboard' },
      { id: 'destination-twin', label: 'Destination Twin', icon: 'deployed_code' },
      { id: 'tourism-intelligence', label: 'Tourism Intelligence', icon: 'monitoring' },
      { id: 'crowd-destination-stress', label: 'Crowd & Stress', icon: 'groups' },
    ],
  },
  {
    title: 'RESILIENCE',
    items: [
      { id: 'risk-resilience', label: 'Risk & Resilience', icon: 'shield' },
      { id: 'disaster-mode', label: 'Disaster Mode', icon: 'warning', alert: true },
      { id: 'live-geospatial-map', label: 'Live Geospatial Map', icon: 'map' },
      { id: 'satellite-intelligence', label: 'Satellite Intel', icon: 'satellite_alt' },
    ],
  },
  {
    title: 'SIMULATION & AI',
    items: [
      { id: 'what-if-simulator', label: 'What-If Simulator', icon: 'tune' },
      { id: 'simulation-results', label: 'Simulation Results', icon: 'analytics' },
      { id: 'intervention-optimizer', label: 'Intervention Optimizer', icon: 'alt_route' },
      { id: 'optimization-explanation', label: 'Optimization Explanation', icon: 'description' },
      { id: 'ai-model-center', label: 'AI Model Center', icon: 'neurology' },
    ],
  },
  {
    title: 'INSIGHTS & GOVERNANCE',
    items: [
      { id: 'tourist-community-insights', label: 'Tourist & Community', icon: 'forum' },
      { id: 'data-hub', label: 'Data Hub', icon: 'database' },
      { id: 'reports-briefs', label: 'Reports & Briefs', icon: 'fact_check' },
      { id: 'notifications', label: 'Notifications', icon: 'notifications' },
    ],
  },
  {
    title: 'SYSTEM',
    items: [
      { id: 'settings', label: 'Settings', icon: 'settings' },
      { id: 'help-architecture', label: 'Help & Architecture', icon: 'account_tree' },
    ],
  },
];

export default function Sidebar({ activeTab, onSelectTab }) {
  return (
    <aside className="fixed left-0 top-0 h-full w-72 bg-surface-container-lowest z-50 flex flex-col shadow-[0_1px_8px_rgba(0,0,0,0.5)] border-r border-[#d4af37]/15 select-none">
      {/* Brand Header */}
      <div 
        onClick={() => onSelectTab('landing')}
        className="h-16 px-gutter flex items-center gap-space-sm bg-surface-container-low cursor-pointer hover:bg-surface-container transition-colors group"
        title="Click to visit Landing Page"
      >
        <div className="w-8 h-8 rounded-lg bg-[#d4af37]/15 border border-[#d4af37]/40 flex items-center justify-center text-[#f2ca50] group-hover:scale-105 transition-transform shadow-[0_0_12px_rgba(212,175,55,0.2)]">
          <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" strokeLinecap="round" strokeLinejoin="round"></path>
          </svg>
        </div>
        <div className="flex flex-col">
          <span className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold group-hover:text-gold-300 transition-colors">
            SafarSaathi
          </span>
          <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant uppercase tracking-widest text-[9px]">
            RESILIENCE OPS // CORE
          </span>
        </div>
      </div>

      {/* Nav List */}
      <div className="flex-1 overflow-y-auto px-space-sm py-space-md custom-scrollbar">
        <nav className="flex flex-col gap-space-md">
          {navGroups.map((group) => (
            <div key={group.title} className="flex flex-col gap-space-xs">
              <span className="px-space-sm font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-[10px] text-slate-400">
                {group.title}
              </span>
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => {
                  const isActive = activeTab === item.id;
                  const isDisaster = item.alert;

                  if (isDisaster) {
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => onSelectTab(item.id)}
                        className={`flex items-center justify-between px-space-sm py-1.5 rounded transition-all text-left w-full ${
                          isActive
                            ? 'bg-error-container/40 text-error border border-error/50 shadow-[0_0_16px_rgba(239,68,68,0.3)]'
                            : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                        }`}
                      >
                        <div className="flex items-center gap-space-sm">
                          <span className="material-symbols-outlined text-[18px] text-error">
                            {item.icon}
                          </span>
                          <span className={`font-body-md text-body-md ${isActive ? 'font-semibold text-error' : ''}`}>
                            {item.label}
                          </span>
                        </div>
                        <span className="w-2 h-2 rounded-full bg-error animate-pulse shadow-[0_0_6px_#ef4444]"></span>
                      </button>
                    );
                  }

                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => onSelectTab(item.id)}
                      className={`flex items-center gap-space-sm px-space-sm py-1.5 rounded transition-all text-left w-full ${
                        isActive
                          ? 'bg-primary-container text-on-primary-container font-semibold shadow-[0_0_12px_rgba(212,175,55,0.25)] border border-primary/40'
                          : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
                      }`}
                    >
                      <span className={`material-symbols-outlined text-[18px] ${isActive ? 'text-on-primary-container' : 'text-slate-400'}`}>
                        {item.icon}
                      </span>
                      <span className="font-body-md text-body-md">
                        {item.label}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </div>

      {/* Footer System Telemetry */}
      <div className="p-space-sm bg-surface-container-low border-t border-[#d4af37]/15">
        <div className="flex items-center justify-between p-space-xs rounded bg-surface-container-lowest border border-white/5">
          <div className="flex items-center gap-space-xs">
            <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
            <span className="font-telemetry-sm text-telemetry-sm text-on-surface-variant text-[10px]">
              SVR-NORTH-01
            </span>
          </div>
          <span className="font-telemetry-sm text-telemetry-sm text-primary font-bold text-[10px]">
            DEMO STATUS
          </span>
        </div>
      </div>
    </aside>
  );
}
