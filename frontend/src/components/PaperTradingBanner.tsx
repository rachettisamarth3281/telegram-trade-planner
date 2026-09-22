import React from 'react';
import { ShieldCheck, Info } from 'lucide-react';

export const PaperTradingBanner: React.FC = () => {
  return (
    <div className="bg-gradient-to-r from-sky-950/80 via-slate-900 to-indigo-950/80 border-y border-sky-500/30 px-4 py-2 text-xs">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-sky-500"></span>
          </span>
          <span className="font-extrabold tracking-wider text-sky-400 uppercase text-[11px] bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
            MANUAL TRADE PLANNING MODE
          </span>
          <span className="text-slate-300 font-medium hidden md:inline">
            • Telegram Signal Analyzer & Trade Planning
          </span>
        </div>

        <div className="flex items-center gap-4 text-slate-400 text-[11px]">
          <div className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Zero Broker Execution</span>
          </div>
          <div className="flex items-center gap-1 hidden sm:flex">
            <Info className="h-3.5 w-3.5 text-sky-400" />
            <span>Copy-Ready Manual Trade Plans</span>
          </div>
        </div>
      </div>
    </div>
  );
};

