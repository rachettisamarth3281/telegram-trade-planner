import React, { useState, useEffect } from 'react';
import {
  Save,
  ShieldCheck,
  Wallet,
  Sliders,
  Scale,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import type { AccountInfo } from '../types';
import { fetchSystemSettings, updateSystemSettings, updateAccount } from '../lib/api';

interface SettingsTabProps {
  account?: AccountInfo;
  onAccountUpdated: () => void;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({ account, onAccountUpdated }) => {
  const [balance, setBalance] = useState('10000');
  const [riskPct, setRiskPct] = useState('1.0');
  const [defaultR, setDefaultR] = useState('2.0');
  const [altRs, setAltRs] = useState('1.0, 1.5, 2.0, 3.0');
  const [minRR, setMinRR] = useState('1.5');
  const [sizingMode, setSizingMode] = useState('FIXED_RISK_AMOUNT');
  const [fixedRiskAmt, setFixedRiskAmt] = useState('100');
  const [marketProvider, setMarketProvider] = useState('MOCK');
  const [executionPolicy, setExecutionPolicy] = useState('CONSERVATIVE');

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const sys = await fetchSystemSettings();
        setDefaultR(sys.default_r_multiple.toString());
        setAltRs(sys.alternative_r_multiples.join(', '));
        setMinRR(sys.min_risk_reward_ratio.toString());
        setSizingMode(sys.position_sizing_mode);
        setFixedRiskAmt(sys.fixed_risk_amount.toString());
        setMarketProvider(sys.market_data_provider);
        setExecutionPolicy(sys.candle_execution_policy);
        setBalance(sys.current_balance.toString());
        setRiskPct(sys.risk_percent.toString());
      } catch (e) {
        console.error('Failed to load system settings', e);
      }
    };
    load();
  }, [account]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);
    setSaveError(null);

    try {
      const parsedAltRs = altRs
        .split(',')
        .map((x) => parseFloat(x.trim()))
        .filter((x) => !isNaN(x) && x > 0);

      await updateSystemSettings({
        default_r_multiple: parseFloat(defaultR),
        alternative_r_multiples: parsedAltRs.length > 0 ? parsedAltRs : [1.0, 1.5, 2.0, 3.0],
        min_risk_reward_ratio: parseFloat(minRR),
        paper_trading_mode: true,
        position_sizing_mode: sizingMode,
        fixed_risk_amount: parseFloat(fixedRiskAmt),
        market_data_provider: marketProvider,
        candle_execution_policy: executionPolicy,
        current_balance: parseFloat(balance),
        risk_percent: parseFloat(riskPct)
      });

      await updateAccount({
        current_balance: parseFloat(balance),
        risk_percent: parseFloat(riskPct),
        default_r_target: parseFloat(defaultR)
      });

      setSaveSuccess(true);
      onAccountUpdated();
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setSaveError(err.message || 'Error updating settings');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Simulation Notice Banner */}
      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex items-start gap-3">
        <ShieldCheck className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-300">
          <div className="font-bold text-emerald-400 text-sm">PAPER TRADING & SIMULATION MODE ACTIVE</div>
          <p className="mt-0.5 text-slate-400">
            This system strictly does not place live broker orders. All trades, sizing calculations, candle triggers, and balances are 100% simulated paper calculations.
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* 1. Risk & R-Multiple Parameters */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center gap-2 border-b border-[#1e293b] pb-3">
            <Sliders className="h-5 w-5 text-sky-400" />
            <h3 className="font-bold text-white text-sm">1. Risk & R-Multiple Configuration</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Default Target R (if no TP)
              </label>
              <select
                value={defaultR}
                onChange={(e) => setDefaultR(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              >
                <option value="1.0">1.0R Target</option>
                <option value="1.5">1.5R Target</option>
                <option value="2.0">2.0R Target (Standard)</option>
                <option value="3.0">3.0R Target</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Alternative R Targets
              </label>
              <input
                type="text"
                value={altRs}
                onChange={(e) => setAltRs(e.target.value)}
                placeholder="1.0, 1.5, 2.0, 3.0"
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              />
              <span className="text-[10px] text-slate-500">Comma-separated multiples</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Minimum Allowed RR
              </label>
              <input
                type="number"
                step="0.1"
                value={minRR}
                onChange={(e) => setMinRR(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              />
              <span className="text-[10px] text-slate-500">Signals below this are flagged LOW_RR</span>
            </div>
          </div>
        </div>

        {/* 2. Position Sizing & Virtual Account Balance */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center gap-2 border-b border-[#1e293b] pb-3">
            <Wallet className="h-5 w-5 text-emerald-400" />
            <h3 className="font-bold text-white text-sm">2. Position Sizing & Account Capital</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Position Sizing Mode
              </label>
              <select
                value={sizingMode}
                onChange={(e) => setSizingMode(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              >
                <option value="FIXED_RISK_AMOUNT">FIXED_RISK_AMOUNT ($ / Trade)</option>
                <option value="FIXED_LOT">FIXED_LOT (Static Lots)</option>
                <option value="PERCENTAGE_RISK">PERCENTAGE_RISK (% of Capital)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Fixed Risk Amount ($ USD)
              </label>
              <input
                type="number"
                step="10"
                value={fixedRiskAmt}
                onChange={(e) => setFixedRiskAmt(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Virtual Balance ($ USD)
              </label>
              <input
                type="number"
                step="100"
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>
        </div>

        {/* 3. Market Data & Execution Policy */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center gap-2 border-b border-[#1e293b] pb-3">
            <Scale className="h-5 w-5 text-indigo-400" />
            <h3 className="font-bold text-white text-sm">3. Market Feed & Candle Ambiguity Policy</h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Market Data Provider
              </label>
              <select
                value={marketProvider}
                onChange={(e) => setMarketProvider(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              >
                <option value="MOCK">MOCK (Simulated Engine Tick Feed)</option>
                <option value="MT5">MT5 (Read-Only MetaTrader 5 Terminal Feed)</option>
              </select>
              <span className="text-[10px] text-slate-500">Only reads market prices; never transmits live orders.</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Candle Dual-Breach Execution Policy
              </label>
              <select
                value={executionPolicy}
                onChange={(e) => setExecutionPolicy(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
              >
                <option value="CONSERVATIVE">CONSERVATIVE (SL Triggers First on Ambiguity)</option>
                <option value="SL_FIRST">SL_FIRST (Prioritize Stop Loss Risk Protection)</option>
                <option value="TP_FIRST">TP_FIRST (Optimistic Target Execution)</option>
                <option value="BAR_CLOSE">BAR_CLOSE (Evaluate at Candle Close)</option>
              </select>
              <span className="text-[10px] text-slate-500">Handles candles that touch both SL and TP in the same bar.</span>
            </div>
          </div>
        </div>

        {/* Action Bar */}
        <div className="flex items-center justify-between p-4 bg-[#111726] border border-[#1e293b] rounded-xl">
          <div className="text-xs font-medium">
            {saveSuccess && (
              <span className="text-emerald-400 flex items-center gap-1.5 font-semibold">
                <CheckCircle2 className="h-4 w-4" /> System parameters updated successfully!
              </span>
            )}
            {saveError && (
              <span className="text-rose-400 flex items-center gap-1.5 font-semibold">
                <AlertTriangle className="h-4 w-4" /> {saveError}
              </span>
            )}
            {!saveSuccess && !saveError && (
              <span className="text-slate-400">Changes apply immediately to upcoming signals and paper trades.</span>
            )}
          </div>

          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white rounded-lg text-xs font-bold transition-all disabled:opacity-50 shadow-md shadow-sky-500/20 cursor-pointer"
          >
            <Save className="h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
};
