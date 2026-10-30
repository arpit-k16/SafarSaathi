import React from 'react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;

  const isError = toast.type === 'error';
  const isWarning = toast.type === 'warning';

  return (
    <div className={`fixed bottom-10 right-10 z-50 p-4 rounded-xl shadow-2xl flex items-center gap-3 transition-all duration-300 transform translate-y-0 border ${
      isError 
        ? 'bg-red-950/95 text-red-100 border-red-500/50 shadow-[0_0_30px_rgba(239,68,68,0.4)]'
        : isWarning
        ? 'bg-amber-950/95 text-amber-100 border-amber-500/50 shadow-[0_0_30px_rgba(245,158,11,0.4)]'
        : 'bg-primary text-on-primary border-[#ffe088] shadow-[0_0_30px_rgba(212,175,55,0.4)]'
    }`}>
      <span className="material-symbols-outlined text-[26px]">
        {isError ? 'emergency_home' : isWarning ? 'warning' : 'task_alt'}
      </span>
      <div className="flex flex-col pr-3">
        <span className="font-headline-sm text-headline-sm leading-tight text-sm font-bold">
          {toast.title || 'System Notification'}
        </span>
        <span className={`font-telemetry-sm text-telemetry-sm text-[11px] ${
          isError ? 'text-red-300' : isWarning ? 'text-amber-200' : 'text-on-primary/80'
        }`}>
          {toast.message}
        </span>
      </div>
      <button 
        type="button" 
        onClick={onClose} 
        className="ml-auto opacity-70 hover:opacity-100 transition-opacity p-1 text-inherit"
      >
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  );
}
