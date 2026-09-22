import React from 'react';
import {
  FileCheck,
  Radio,
  TrendingUp,
  BookOpen,
  BarChart3,
  Terminal,
  Settings as SettingsIcon,
  Layers
} from 'lucide-react';
import type { AccountRiskStatusV1 } from '../types';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  accountRisk?: AccountRiskStatusV1;
  isWsConnected: boolean;
  readyPlansCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  accountRisk,
  isWsConnected,
  readyPlansCount,
}) => {
  const tabs = [
    { id: 'trade-plans', label: 'Trade Plans', icon: FileCheck, badge: readyPlansCount > 0 ? readyPlansCount : undefined },
    { id: 'signals', label: 'Signal Feed', icon: Radio },
    { id: 'live-trades', label: 'Simulated Trades', icon: TrendingUp },
    { id: 'journal', label: 'Journal', icon: BookOpen },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'sandbox', label: 'Sandbox', icon: Terminal },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  const currentBal = accountRisk ? accountRisk.current_balance : 50000.0;

  return (
    <header className="bg-[#0f172a] border-b border-[#1e293b] sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Title */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setActiveTab('trade-plans')}>
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <Layers className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">TRADE PLANNER</span>
                <span className="text-[10px] uppercase font-extrabold px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/30">
                  V1 Manual
                </span>
              </div>
              <p className="text-xs text-slate-400">Telegram Signal Analyzer & Sizing Platform</p>
            </div>
          </div>

          {/* Nav Tabs */}
          <nav className="hidden md:flex items-center space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                  {tab.badge !== undefined && (
                    <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-mono font-bold">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Account Balance & WS Status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="flex flex-col text-right">
                <span className="text-[10px] text-slate-400 font-semibold tracking-wider">BALANCE (INR)</span>
                <span className="text-sm font-bold text-slate-100 font-mono">
                  ₹{currentBal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
              <div className={`h-2 w-2 rounded-full ${isWsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
                {isWsConnected ? 'Live Feed' : 'Offline'}
              </span>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        <div className="md:hidden flex items-center space-x-1 pb-3 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span className="px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px]">
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
