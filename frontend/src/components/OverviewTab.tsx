import React, { useState } from 'react';
import {
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Send,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  Zap,
  Target,
  Radio,
  BarChart2
} from 'lucide-react';
import type { CompleteAnalyticsReport, SignalItem, PaperTradeItem } from '../types';
import { ingestSignal } from '../lib/api';

interface OverviewTabProps {
  analytics?: CompleteAnalyticsReport;
  recentSignals: SignalItem[];
  openTrades: PaperTradeItem[];
  onSignalIngested: () => void;
  onNavigateTab: (tab: string) => void;
  onSelectSignal: (sig: SignalItem) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  analytics,
  recentSignals,
  openTrades,
  onSignalIngested,
  onNavigateTab,
  onSelectSignal,
}) => {
  const [inputText, setInputText] = useState('');
  const [channelTitle, setChannelTitle] = useState('VIP Channel');
  const [targetR, setTargetR] = useState(2.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const sigs = analytics?.signals;
  const trds = analytics?.trades;
  const perf = analytics?.performance;

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    try {
      const res = await ingestSignal(inputText, { channel_title: channelTitle, target_r: targetR });
      if (res.validation_status === 'VALID') {
        setSubmitSuccess(`Signal validated & Paper Trade #${res.paper_trade_id?.slice(0, 8)} opened!`);
      } else {
        setSubmitSuccess(`Signal audited as ${res.validation_status}: ${res.rejection_reason || 'Recorded'}`);
      }
      setInputText('');
      onSignalIngested();
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to ingest signal');
    } finally {
      setIsSubmitting(false);
    }
  };

  const loadExample = (ex: string) => {
    setInputText(ex);
  };

  return (
    <div className="space-y-6">
      {/* 8 Core KPI Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        {/* 1. Total Signals */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total Signals</span>
            <Radio className="h-3.5 w-3.5 text-sky-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-white font-mono">{sigs?.total_signals ?? 0}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">Ingested</div>
          </div>
        </div>

        {/* 2. Valid Signals */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Valid Signals</span>
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-emerald-400 font-mono">{sigs?.valid_signals ?? 0}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {sigs?.validity_rate_pct ?? 0}% validity
            </div>
          </div>
        </div>

        {/* 3. Open Trades */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Open Trades</span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-white font-mono">{trds?.open_trades ?? openTrades.length}</div>
            <div className="text-[10px] text-emerald-400 mt-0.5 font-semibold">Active simulated</div>
          </div>
        </div>

        {/* 4. Closed Trades */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Closed Trades</span>
            <Clock className="h-3.5 w-3.5 text-slate-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-slate-200 font-mono">{trds?.closed_trades ?? 0}</div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {trds?.wins ?? 0}W / {trds?.losses ?? 0}L
            </div>
          </div>
        </div>

        {/* 5. Win Rate */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Win Rate</span>
            <Target className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-white font-mono">{trds?.win_rate_pct ?? 0}%</div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {trds?.breakeven ? `${trds.breakeven} BE` : 'Observed'}
            </div>
          </div>
        </div>

        {/* 6. Total R */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Total R</span>
            {perf && perf.total_realized_r >= 0 ? (
              <ArrowUpRight className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <ArrowDownRight className="h-3.5 w-3.5 text-rose-400" />
            )}
          </div>
          <div className="mt-2">
            <div className={`text-xl font-bold font-mono ${perf && perf.total_realized_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {perf ? `${perf.total_realized_r >= 0 ? '+' : ''}${perf.total_realized_r}R` : '0.00R'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5 font-mono">
              ${perf ? perf.net_pnl_usd.toFixed(2) : '0.00'}
            </div>
          </div>
        </div>

        {/* 7. Average R */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Average R</span>
            <Zap className="h-3.5 w-3.5 text-indigo-400" />
          </div>
          <div className="mt-2">
            <div className={`text-xl font-bold font-mono ${perf && perf.average_r_per_trade >= 0 ? 'text-indigo-400' : 'text-rose-400'}`}>
              {perf ? `${perf.average_r_per_trade >= 0 ? '+' : ''}${perf.average_r_per_trade}R` : '0.00R'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Per trade</div>
          </div>
        </div>

        {/* 8. Profit Factor */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-3.5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[10px] font-bold uppercase tracking-wider">Profit Factor</span>
            <BarChart2 className="h-3.5 w-3.5 text-sky-400" />
          </div>
          <div className="mt-2">
            <div className="text-xl font-bold text-white font-mono">
              {perf ? perf.profit_factor : '1.00'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Ratio</div>
          </div>
        </div>
      </div>

      {/* Main Grid: Pipeline Ingestion & Live Trades Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Instant Signal Pipeline Ingestion Box */}
        <div className="lg:col-span-5 bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-sky-400" />
              <h2 className="font-semibold text-white">Ingest Signal (Simulation)</h2>
            </div>
            <span className="text-[11px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 font-medium">
              Simulation Only
            </span>
          </div>

          <form onSubmit={handleIngest} className="space-y-3">
            <div>
              <label className="text-xs text-slate-400 font-medium block mb-1">Telegram Text Signal</label>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="e.g. Sell gold @ 4350.53&#10;SL 4358"
                rows={4}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg p-3 text-xs text-slate-100 font-mono placeholder:text-slate-600 focus:outline-none focus:border-sky-500 transition-colors resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400 font-medium block mb-1">Channel Source</label>
                <input
                  type="text"
                  value={channelTitle}
                  onChange={(e) => setChannelTitle(e.target.value)}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 font-medium block mb-1">Target R if no TP</label>
                <select
                  value={targetR}
                  onChange={(e) => setTargetR(parseFloat(e.target.value))}
                  className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  <option value={1.0}>1.0R Target</option>
                  <option value={1.5}>1.5R Target</option>
                  <option value={2.0}>2.0R Target (Default)</option>
                  <option value={3.0}>3.0R Target</option>
                </select>
              </div>
            </div>

            {submitError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            {submitSuccess && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-400 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{submitSuccess}</span>
              </div>
            )}

            <div className="flex items-center justify-between pt-1">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => loadExample("Sell gold @ 4350.53\nSL 4358")}
                  className="text-[11px] px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  Gold Example
                </button>
                <button
                  type="button"
                  onClick={() => loadExample("BUY EURUSD CMP 1.08500\nSL 1.08000\nTP1 1.09000\nTP2 1.09500")}
                  className="text-[11px] px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                >
                  EURUSD Example
                </button>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !inputText.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-bold transition-all shadow-md shadow-sky-500/20 cursor-pointer"
              >
                <Send className="h-3.5 w-3.5" />
                {isSubmitting ? 'Evaluating...' : 'Ingest & Simulate'}
              </button>
            </div>
          </form>
        </div>

        {/* Right: Active Open Paper Trades Table Preview */}
        <div className="lg:col-span-7 bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-400" />
              <h2 className="font-semibold text-white">Live Open Trades</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                {openTrades.length} open
              </span>
            </div>
            <button
              onClick={() => onNavigateTab('live-trades')}
              className="text-xs text-sky-400 hover:text-sky-300 transition-colors font-medium"
            >
              Monitor live & simulate ticks →
            </button>
          </div>

          {openTrades.length === 0 ? (
            <div className="h-52 flex flex-col items-center justify-center border border-dashed border-[#1e293b] rounded-xl text-slate-500 text-xs">
              <Clock className="h-6 w-6 mb-2 opacity-40" />
              <span>No active simulated trades running. Ingest a valid signal above.</span>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#1e293b] text-slate-400 font-medium">
                    <th className="pb-2.5">Symbol</th>
                    <th className="pb-2.5">Side</th>
                    <th className="pb-2.5">Entry</th>
                    <th className="pb-2.5">Stop Loss</th>
                    <th className="pb-2.5">Target TP</th>
                    <th className="pb-2.5">Target R</th>
                    <th className="pb-2.5 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e293b]/60">
                  {openTrades.slice(0, 5).map((t) => (
                    <tr key={t.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3 font-bold text-slate-100">{t.symbol}</td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                          t.side === 'BUY' ? 'bg-emerald-500/15 text-emerald-400' : 'bg-rose-500/15 text-rose-400'
                        }`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="py-3 font-mono text-slate-300">{t.entry_price}</td>
                      <td className="py-3 font-mono text-rose-400">{t.effective_sl}</td>
                      <td className="py-3 font-mono text-emerald-400">{t.active_tp || 'Dynamic'}</td>
                      <td className="py-3 font-mono text-sky-400">{t.target_r_multiple}R</td>
                      <td className="py-3 text-right">
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold animate-pulse">
                          RUNNING
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Recent Signal Stream Preview */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="h-5 w-5 text-sky-400" />
            <h2 className="font-semibold text-white">Recent Signals Stream</h2>
          </div>
          <button
            onClick={() => onNavigateTab('signals')}
            className="text-xs text-sky-400 hover:text-sky-300 transition-colors font-medium"
          >
            Full signal feed & audit →
          </button>
        </div>

        {recentSignals.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs border border-dashed border-[#1e293b] rounded-xl">
            No signals received yet.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentSignals.slice(0, 3).map((sig) => (
              <div
                key={sig.id}
                onClick={() => onSelectSignal(sig)}
                className="bg-[#0b0f19] border border-[#1e293b] hover:border-sky-500/40 rounded-lg p-4 flex flex-col justify-between space-y-3 cursor-pointer transition-colors shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-slate-100 text-sm">{sig.symbol || 'PARSING...'}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                      sig.validation_status === 'VALID'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : sig.validation_status.startsWith('SKIPPED')
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                    }`}>
                      {sig.validation_status}
                    </span>
                  </div>
                  <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap line-clamp-3 bg-slate-900/60 p-2.5 rounded border border-slate-800">
                    {sig.raw_text}
                  </pre>
                </div>

                {sig.metrics ? (
                  <div className="text-[11px] grid grid-cols-3 gap-1 pt-2 border-t border-slate-800 text-slate-400 font-mono">
                    <div>Risk: <span className="text-rose-400">{sig.metrics.risk_pips}p</span></div>
                    <div>1R: <span className="text-slate-200">{sig.metrics.r1_target}</span></div>
                    <div>2R: <span className="text-emerald-400">{sig.metrics.r2_target}</span></div>
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-500 pt-2 border-t border-slate-800 line-clamp-1">
                    {sig.rejection_reason || 'No calculation metrics'}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
