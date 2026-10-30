import React, { useState } from 'react';

const CORRIDORS = [
  {
    id: 'garhwal',
    name: 'Garhwal Arc',
    sub: 'Rishikesh-Devprayag-Kedarnath corridor',
    tier: 'TIER-1 MONITORED',
    telemetry: 'NODES: 32 DEPLOYED // SMR: 0.12mm/hr',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
  },
  {
    id: 'rishikesh',
    name: 'Rishikesh Core',
    sub: 'Tapovan, Laxman Jhula & Ganga Riverbank',
    tier: 'PRIMARY • 108 Kms²',
    telemetry: 'ACTIVE TWIN MESH // 42,180 PAX CURRENT',
    isPrimary: true,
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        <path d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" strokeLinecap="round" strokeLinejoin="round"></path>
        <path d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
  },
  {
    id: 'kumaon',
    name: 'Kumaon Belt',
    sub: 'Nainital, Bhimtal & Almora Lake Basin',
    tier: 'ELEVATED STRESS',
    telemetry: 'LAKE BASIN SENSORS // 18 SITES',
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M13 10V3L4 14h7v7l9-11h-7z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
  },
  {
    id: 'mandakini',
    name: 'Upper Mandakini',
    sub: 'Sonprayag to Kedarnath Base Transit',
    tier: 'HIGH HAZARD SENSITIVITY',
    telemetry: 'INSAR SLIP RADAR // 4 HIGH-DEF ARRAYS',
    isWarning: true,
    icon: (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
        <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" strokeLinecap="round" strokeLinejoin="round"></path>
      </svg>
    ),
  },
];

export default function LandingPage({ onNavigate }) {
  const [selectedCorridor, setSelectedCorridor] = useState('rishikesh');
  const [corridorFilter, setCorridorFilter] = useState('active');

  return (
    <div className="min-h-screen bg-[#080a0f] text-slate-200 antialiased selection:bg-[#d4af37] selection:text-black subtle-grid">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#d4af37]/15 bg-[#080a0f]/85 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          
          {/* Logo & Tier Badge */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onNavigate('landing')}>
            <div className="flex items-center space-x-2.5 text-white tracking-tight text-xl font-bold">
              <div className="w-7 h-7 rounded-lg bg-[#d4af37]/20 border border-[#d4af37]/50 flex items-center justify-center text-[#f2ca50]">
                <svg className="w-4 h-4 text-[#f2ca50]" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" strokeLinecap="round" strokeLinejoin="round"></path>
                </svg>
              </div>
              <span className="tracking-tight font-extrabold text-white">SafarSaathi</span>
            </div>
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-[#d4af37]/40 text-[#f2ca50] bg-[#d4af37]/10 font-medium">
              R-TIER v4.2
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center space-x-8 text-xs font-medium text-slate-400">
            <button 
              type="button" 
              onClick={() => onNavigate('overview')} 
              className="text-white hover:text-[#f2ca50] transition-colors"
            >
              Overview
            </button>
            <button 
              type="button" 
              onClick={() => onNavigate('destination-twin')} 
              className="hover:text-[#f2ca50] transition-colors"
            >
              Digital Twin
            </button>
            <button 
              type="button" 
              onClick={() => onNavigate('tourism-intelligence')} 
              className="hover:text-[#f2ca50] transition-colors"
            >
              Intelligence
            </button>
            <button 
              type="button" 
              onClick={() => onNavigate('what-if-simulator')} 
              className="hover:text-[#f2ca50] transition-colors"
            >
              What-If Simulation
            </button>
            <button 
              type="button" 
              onClick={() => onNavigate('disaster-mode')} 
              className="hover:text-[#f2ca50] transition-colors flex items-center gap-1.5"
            >
              <span>Disaster Mode</span>
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
            </button>
          </nav>

          {/* Right Telemetry & Actions */}
          <div className="flex items-center space-x-5 text-xs font-mono">
            <div className="hidden lg:flex items-center space-x-2 text-[11px] text-[#f2ca50] bg-[#d4af37]/10 px-2.5 py-1 rounded border border-[#d4af37]/30">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#f2ca50] animate-ping"></span>
              <span>DEMO DATA / STATIC PREVIEW</span>
            </div>

            <button
              type="button"
              onClick={() => onNavigate('overview')}
              className="px-4 py-1.5 rounded bg-gradient-to-r from-[#f2ca50] to-[#d4af37] text-slate-950 font-bold text-xs hover:from-[#ffe088] hover:to-[#f2ca50] transition-all glow-gold-btn"
            >
              Launch Command Deck
            </button>
          </div>

        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-36 pb-20 md:pt-44 md:pb-28 overflow-hidden subtle-grid">
        <div className="absolute inset-0 hero-vignette pointer-events-none"></div>
        <div className="relative max-w-5xl mx-auto px-6 text-center">
          
          {/* Eyebrow Tag */}
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-[#d4af37]/35 bg-[#d4af37]/10 text-[#f2ca50] text-[10px] md:text-xs font-mono font-medium tracking-ultra uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-[#f2ca50] shadow-[0_0_6px_#f2ca50]"></span>
            Geospatial Resilience &amp; Tourism Intelligence
          </div>

          {/* Giant Title */}
          <h1 className="text-5xl md:text-7xl font-extrabold text-white tracking-tight mb-6 leading-tight">
            SafarSaathi
          </h1>

          {/* Sub-headline */}
          <p className="max-w-2xl mx-auto text-sm md:text-base text-slate-300 font-normal leading-relaxed mb-8">
            AI-Driven Geospatial Intelligence &amp; Carrying Capacity Analytics for Mountain Destinations. Precision decision support for regional administrators, NDMA, and tourism authorities.
          </p>

          {/* Active Sync Badge */}
          <div className="inline-flex items-center space-x-2 text-[#f2ca50] font-mono text-[11px] tracking-wider px-4 py-1.5 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/35 shadow-[0_0_15px_rgba(212,175,55,0.15)]">
            <span className="text-xs text-[#ffd700]">▶</span>
            <span>LOCAL BACKEND CONNECTED VIEWS · LIVE TELEMETRY NOT AVAILABLE</span>
          </div>

          {/* Quick Access Action Deck Pill Links */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => onNavigate('overview')}
              className="px-4 py-2 rounded-lg bg-surface-container border border-[#d4af37]/30 hover:border-[#d4af37] text-white hover:text-[#f2ca50] text-xs font-mono flex items-center gap-2 transition-all"
            >
              <span className="material-symbols-outlined text-[16px] text-primary">dashboard</span>
              <span>Overview Deck</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('destination-twin')}
              className="px-4 py-2 rounded-lg bg-surface-container border border-[#d4af37]/30 hover:border-[#d4af37] text-white hover:text-[#f2ca50] text-xs font-mono flex items-center gap-2 transition-all"
            >
              <span className="material-symbols-outlined text-[16px] text-primary">deployed_code</span>
              <span>3D Digital Twin</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('what-if-simulator')}
              className="px-4 py-2 rounded-lg bg-surface-container border border-[#d4af37]/30 hover:border-[#d4af37] text-white hover:text-[#f2ca50] text-xs font-mono flex items-center gap-2 transition-all"
            >
              <span className="material-symbols-outlined text-[16px] text-primary">tune</span>
              <span>What-If Simulator</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('disaster-mode')}
              className="px-4 py-2 rounded-lg bg-red-950/30 border border-red-500/40 hover:border-red-500 text-red-200 hover:text-white text-xs font-mono flex items-center gap-2 transition-all shadow-[0_0_12px_rgba(239,68,68,0.2)]"
            >
              <span className="material-symbols-outlined text-[16px] text-red-400">warning</span>
              <span>Disaster Mode</span>
            </button>
          </div>

          {/* Animated Down Chevron */}
          <div className="mt-12 flex justify-center text-[#d4af37]/50 animate-bounce">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
              <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round"></path>
            </svg>
          </div>

        </div>
      </section>

      {/* Corridor Selection Section */}
      <section className="relative py-16 border-t border-[#d4af37]/15 bg-[#080a0f]">
        <div className="max-w-7xl mx-auto px-6">
          
          {/* Section Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-6">
            <div>
              <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight">
                Select Operational Corridor
              </h2>
              <p className="mt-2 text-xs md:text-sm text-slate-400 max-w-xl">
                Access localized carrying capacity models, predictive choke hazards, live InSAR slip telemetry, and hydraulic flood vectors for vulnerable destination sectors.
              </p>
            </div>

            {/* Filter Pills */}
            <div className="inline-flex p-1 bg-[#0c0e14] border border-[#d4af37]/20 rounded-lg self-start md:self-auto font-mono text-xs">
              <button
                type="button"
                onClick={() => setCorridorFilter('active')}
                className={`px-3 py-1.5 rounded font-medium transition-colors ${
                  corridorFilter === 'active'
                    ? 'bg-[#d4af37]/20 text-[#f2ca50] border border-[#d4af37]/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Active Corridors
              </button>
              <button
                type="button"
                onClick={() => setCorridorFilter('waitlist')}
                className={`px-3 py-1.5 rounded font-medium transition-colors ${
                  corridorFilter === 'waitlist'
                    ? 'bg-[#d4af37]/20 text-[#f2ca50] border border-[#d4af37]/40 shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Waitlist / Scheduled
              </button>
            </div>
          </div>

          {/* 4 Card Corridor Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
            {CORRIDORS.map((corridor) => {
              const isSelected = selectedCorridor === corridor.id;

              return (
                <div
                  key={corridor.id}
                  onClick={() => setSelectedCorridor(corridor.id)}
                  className={`group relative p-5 rounded-xl transition duration-200 cursor-pointer flex flex-col justify-between h-52 ${
                    isSelected
                      ? 'bg-[#12151e] border-2 border-[#d4af37] glow-gold-card'
                      : 'bg-[#0c0e14] border border-[#d4af37]/20 hover:border-[#d4af37]/45'
                  }`}
                >
                  {/* Selected Indicator Dot */}
                  {isSelected && (
                    <span className="absolute top-3.5 right-3.5 w-2 h-2 rounded-full bg-[#ffd700] shadow-[0_0_8px_#ffd700]"></span>
                  )}

                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center transition-colors ${
                        isSelected
                          ? 'bg-[#d4af37]/20 border border-[#d4af37]/50 text-[#f2ca50]'
                          : 'bg-white/[0.03] border border-white/[0.08] text-slate-400 group-hover:text-[#f2ca50]'
                      }`}>
                        {corridor.icon}
                      </div>

                      <span className={`text-[9px] font-mono tracking-wider px-2 py-0.5 rounded uppercase ${
                        corridor.isWarning
                          ? 'bg-amber-950/40 text-amber-400 border border-amber-500/30'
                          : isSelected
                          ? 'bg-[#d4af37]/20 text-[#f2ca50] border border-[#d4af37]/40 font-semibold'
                          : 'bg-white/[0.04] text-slate-400 border border-white/5'
                      }`}>
                        {corridor.tier}
                      </span>
                    </div>

                    <h3 className={`text-lg font-bold transition-colors ${
                      isSelected ? 'text-white tracking-tight' : 'text-white group-hover:text-[#f2ca50]'
                    }`}>
                      {corridor.name}
                    </h3>
                    <p className={`text-xs mt-1 ${isSelected ? 'text-slate-300' : 'text-slate-400'}`}>
                      {corridor.sub}
                    </p>
                  </div>

                  <div className={`text-[10px] font-mono tracking-wider ${
                    isSelected ? 'text-[#f2ca50] font-semibold' : 'text-slate-500'
                  }`}>
                    {corridor.telemetry}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Centered Action Button */}
          <div className="flex justify-center mt-8">
            <button
              type="button"
              onClick={() => onNavigate('overview')}
              className="inline-flex items-center space-x-2 px-8 py-3.5 rounded-lg bg-gradient-to-r from-[#f2ca50] via-[#d4af37] to-[#b8860b] hover:from-[#ffe088] hover:to-[#d4af37] text-slate-950 font-bold text-sm transition-all duration-200 glow-gold-btn shadow-[0_0_25px_rgba(212,175,55,0.4)]"
            >
              <span>Continue to Overview Dashboard</span>
              <span className="text-base font-bold">→</span>
            </button>
          </div>

        </div>
      </section>

      {/* Data Residency & Institutional Integrity */}
      <section className="py-20 border-t border-[#d4af37]/15 bg-[#0a0c12]">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            
            {/* Left Column: Data Governance */}
            <div className="lg:col-span-6">
              <h2 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight leading-snug">
                Data Residency &amp;<br />Institutional Integrity
              </h2>
              <p className="mt-4 text-slate-300 text-sm md:text-base leading-relaxed max-w-lg">
                Local research prototype with historical tourism data, source metadata and experimental saved pipelines. Live InSAR, IoT and CWC feeds, institutional certification and operational emergency dispatch are not implemented.
              </p>
              <div className="mt-6 flex flex-wrap gap-4 text-xs font-mono text-slate-400">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#f2ca50] shadow-[0_0_6px_#f2ca50]"></span>
                  Experimental Research Pipelines
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#f2ca50] shadow-[0_0_6px_#f2ca50]"></span>
                  Local Read-Only Source Adapters
                </span>
              </div>
            </div>

            {/* Right Column: High-Impact Metrics */}
            <div className="lg:col-span-6 grid grid-cols-1 sm:grid-cols-2 gap-8 lg:pl-10">
              <div className="border-l-2 border-[#d4af37]/60 pl-5">
                <span className="block text-[11px] font-mono text-slate-400 uppercase tracking-widest">
                  Live Telemetry Records
                </span>
                <div className="mt-2 text-4xl lg:text-5xl font-extrabold text-white tracking-tight font-sans">
                  N/A
                </div>
                <span className="mt-2 block text-[10px] font-mono text-[#f2ca50] tracking-wider uppercase font-medium">
                  Live Sensor Feed Not Available
                </span>
              </div>

              <div className="border-l-2 border-[#d4af37]/60 pl-5">
                <span className="block text-[11px] font-mono text-slate-400 uppercase tracking-widest">
                  Model Evaluation
                </span>
                <div className="mt-2 text-4xl lg:text-5xl font-extrabold text-white tracking-tight font-sans">
                  Scoped
                </div>
                <span className="mt-2 block text-[10px] font-mono text-[#f2ca50] tracking-wider uppercase font-medium">
                  Recorded Metrics in AI Model Center
                </span>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* Global Footer */}
      <footer className="border-t border-[#d4af37]/15 bg-[#06080c] py-10 text-xs">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 pb-6 border-b border-white/[0.04]">
            <div>
              <span className="font-bold text-white text-sm">SafarSaathi</span>
              <span className="text-slate-400 text-[11px] ml-2 font-mono">
                // Collaborative Prototype v4.2 | CSIR - NDMA - MoT Framework
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-6 font-mono text-[11px] text-slate-400">
              <button type="button" onClick={() => onNavigate('overview')} className="hover:text-[#f2ca50] transition-colors uppercase">Command Deck</button>
              <button type="button" onClick={() => onNavigate('destination-twin')} className="hover:text-[#f2ca50] transition-colors uppercase">Digital Twin</button>
              <button type="button" onClick={() => onNavigate('what-if-simulator')} className="hover:text-[#f2ca50] transition-colors uppercase">Simulator</button>
              <button type="button" onClick={() => onNavigate('disaster-mode')} className="hover:text-red-400 transition-colors uppercase">Disaster Mode</button>
              <button type="button" onClick={() => onNavigate('overview')} className="text-[#f2ca50] hover:underline uppercase font-medium">Officer Login</button>
            </div>
          </div>

          <div className="mt-6 flex flex-col sm:flex-row items-center justify-between text-[10px] font-mono text-slate-500">
            <div>© 2025 SAFARSAATHI GEOSPATIAL INTELLIGENCE PROGRAM. ALL RIGHTS RESERVED.</div>
            <div className="mt-2 sm:mt-0 tracking-wide text-[#f2ca50]/90">
              RESEARCH DEMO / SIMULATION MODE • NOT A LIVE CIVIL DEFENSE DISPATCH
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
