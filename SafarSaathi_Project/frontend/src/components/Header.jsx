import React, { useState, useEffect } from 'react';

const SECTORS = [
  'Garhwal Arc // Rishikesh Core',
  'Kedarnath High-Altitude Corridor',
  'Badrinath Gateway - Joshimath',
  'Tehri Catchment Bypass',
  'Kumaon Lake Basin // Nainital',
];

export default function Header({ 
  currentSector = 'Garhwal Arc // Rishikesh Core', 
  onSectorChange, 
  onNavigateHome,
  onEmergencyEscalate,
  activeTab
}) {
  const [timeStr, setTimeStr] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [audioActive, setAudioActive] = useState(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const day = String(now.getDate()).padStart(2, '0');
      const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
      const month = months[now.getMonth()];
      const hours = String(now.getHours()).padStart(2, '0');
      const mins = String(now.getMinutes()).padStart(2, '0');
      const secs = String(now.getSeconds()).padStart(2, '0');
      setTimeStr(`${day} ${month} | ${hours}:${mins}:${secs} IST`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="fixed top-0 left-72 right-0 h-16 bg-surface-container-lowest/90 backdrop-blur-xl z-40 border-b border-[#d4af37]/15 shadow-[0_1px_8px_rgba(0,0,0,0.4)]">
      <div className="h-16 w-full px-gutter-lg flex items-center justify-between gap-space-md">
        
        {/* Left: Sector Selector & Time Clock */}
        <div className="flex items-center gap-space-md">
          {/* Sector Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-space-sm px-space-sm py-1.5 rounded bg-surface-container-high border border-white/5 hover:border-[#d4af37]/30 transition-colors text-left"
            >
              <span className="material-symbols-outlined text-[16px] text-primary">explore</span>
              <span className="font-telemetry-md text-telemetry-md text-on-surface tracking-wide text-xs">
                {currentSector}
              </span>
              <span className="material-symbols-outlined text-[16px] text-slate-400">arrow_drop_down</span>
            </button>

            {dropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-72 rounded bg-surface-container-highest border border-[#d4af37]/25 shadow-2xl py-1 z-50">
                <div className="px-3 py-1 text-[9px] font-mono text-on-surface-variant uppercase tracking-wider border-b border-white/5">
                  Select Monitored Sector
                </div>
                {SECTORS.map((sector) => (
                  <button
                    key={sector}
                    type="button"
                    onClick={() => {
                      if (onSectorChange) onSectorChange(sector);
                      setDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs font-mono transition-colors flex items-center justify-between ${
                      currentSector === sector
                        ? 'bg-primary/15 text-primary font-semibold'
                        : 'text-slate-300 hover:bg-surface-container hover:text-white'
                    }`}
                  >
                    <span>{sector}</span>
                    {currentSector === sector && (
                      <span className="material-symbols-outlined text-[14px] text-primary">check</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Time Clock */}
          <div className="hidden xl:flex items-center gap-space-xs px-space-sm py-1.5 rounded bg-surface-container-high border border-white/5">
            <span className="material-symbols-outlined text-[16px] text-on-surface-variant">schedule</span>
            <span className="font-telemetry-md text-telemetry-md text-on-surface-variant text-xs">
              {timeStr || 'LIVE IST'}
            </span>
          </div>
        </div>

        {/* Right: Emergency Quick Action, Audio Toggle, Demo Pill, User */}
        <div className="flex items-center gap-space-md">
          {/* Landing page link */}
          <button
            type="button"
            onClick={onNavigateHome}
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-surface-container hover:bg-surface-container-high border border-white/10 text-xs text-slate-300 hover:text-primary transition-colors"
            title="View Public Landing Page"
          >
            <span className="material-symbols-outlined text-[16px]">home</span>
            <span className="font-mono text-[11px]">Portal</span>
          </button>

          {/* Audio Simulator Toggle */}
          <button
            type="button"
            onClick={() => setAudioActive(!audioActive)}
            className={`p-1.5 rounded border transition-colors flex items-center gap-1 text-xs font-mono ${
              audioActive
                ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 shadow-[0_0_10px_rgba(245,158,11,0.3)]'
                : 'bg-surface-container text-slate-400 border-white/5 hover:text-slate-200'
            }`}
            title="Simulated Audio Telemetry"
          >
            <span className="material-symbols-outlined text-[16px]">
              {audioActive ? 'volume_up' : 'volume_off'}
            </span>
            <span className="text-[10px] hidden sm:inline">
              {audioActive ? 'AUDIO ON' : 'MUTE'}
            </span>
          </button>

          {/* Disaster Mode Quick Escalate (if not on disaster mode already) */}
          {activeTab !== 'disaster-mode' && (
            <button
              type="button"
              onClick={onEmergencyEscalate}
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded bg-red-950/40 border border-red-500/40 text-red-300 hover:bg-red-900/50 hover:text-white transition-all text-xs font-mono shadow-[0_0_12px_rgba(239,68,68,0.25)]"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span>
              <span>CRISIS ESCALATION</span>
            </button>
          )}

          {/* Demo Mode Badge */}
          <div className="flex items-center gap-space-xs px-space-sm py-1 rounded bg-secondary-container text-on-secondary-container shadow-sm border border-secondary/30">
            <span className="w-1.5 h-1.5 rounded-full bg-on-secondary-container animate-ping"></span>
            <span className="font-telemetry-sm text-telemetry-sm uppercase font-semibold text-[10px]">
              BACKEND DATA // DEMO SCHEMATICS
            </span>
          </div>

          {/* User Profile */}
          <div className="flex items-center gap-space-sm">
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-on-primary font-bold shadow-[0_0_12px_rgba(212,175,55,0.4)] cursor-pointer" title="Officer In-Charge // CSIR NDMA Tier-1">
              <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
            </div>
          </div>
        </div>

      </div>
    </header>
  );
}
