import React from 'react';
import {
  ArrowRight,
  Shield,
  Target,
  Zap,
  CheckCircle2,
  Activity,
  Layers,
  Scale
} from 'lucide-react';
import type { SignalItem, PaperTradeItem } from '../types';

interface SignalTimelineViewProps {
  signal: SignalItem;
  trade?: PaperTradeItem | null;
}

export const SignalTimelineView: React.FC<SignalTimelineViewProps> = ({ signal, trade }) => {
  const side = signal.side || 'UNKNOWN';
  const isBuy = side === 'BUY';

  // Parse JSON payloads if present
  let targets: number[] = signal.provider_tps || [];
  if (signal.targets_json) {
    try {
      targets = JSON.parse(signal.targets_json);
    } catch {
      // fallback
    }
  }

  let providerOutcomes: any[] = [];
  if (signal.provider_outcomes_json) {
    try {
      providerOutcomes = JSON.parse(signal.provider_outcomes_json);
    } catch {
      // fallback
    }
  }

  let managementEvents: any[] = [];
  if (signal.management_events_json) {
    try {
      managementEvents = JSON.parse(signal.management_events_json);
    } catch {
      // fallback
    }
  }

  const hasZone = signal.entry_zone_low !== undefined && signal.entry_zone_high !== undefined && signal.entry_zone_low !== null && signal.entry_zone_high !== null;
  const entryDisplay = hasZone
    ? `${signal.entry_zone_low} – ${signal.entry_zone_high} (Ref: ${signal.entry_reference_price ?? signal.entry_price})`
    : signal.entry_price?.toString() || 'Pending Entry';

  const providerClaimedPips = trade?.provider_claimed_pips;
  const providerClaimedStatus = trade?.provider_claimed_status || (providerOutcomes.length > 0 ? providerOutcomes[providerOutcomes.length - 1]?.text : null);

  return (
    <div className="space-y-6">
      {/* 1. Multi-Message Sequence Timeline */}
      <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Multi-Message Sequence Lifecycle
            </span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-400">
            {signal.message_type || 'SIGNAL_ENTRY'}
          </span>
        </div>

        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {/* Step 1: Initial Entry & Zone Discovery */}
          <div className="relative group">
            <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-sky-500 border-2 border-[#0b0f19] shadow-sm" />
            <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                  <span>1. Signal Entry & Zone Extraction</span>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-black ${isBuy ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                    {side}
                  </span>
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(signal.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="text-xs font-mono text-slate-300">
                <span className="text-slate-500">Entry Range: </span>
                <span className="font-bold text-slate-100">{entryDisplay}</span>
                {signal.execution_style && (
                  <span className="ml-2 text-[10px] px-1.5 py-0.2 bg-slate-800 text-sky-300 rounded">
                    {signal.execution_style}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Step 2: Stop Loss Verification */}
          <div className="relative group">
            <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-rose-500 border-2 border-[#0b0f19] shadow-sm" />
            <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                  <Shield className="h-3.5 w-3.5 text-rose-400" />
                  <span>2. Stop Loss Protection Level</span>
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  {signal.provider_sl ? 'Verified' : 'Pending Update'}
                </span>
              </div>
              <div className="text-xs font-mono">
                {signal.provider_sl ? (
                  <span className="text-rose-400 font-bold">SL: {signal.provider_sl} (Zero Assumption Enforced)</span>
                ) : (
                  <span className="text-amber-400">Awaiting separate SL Telegram message</span>
                )}
              </div>
            </div>
          </div>

          {/* Step 3: Targets & Multi-Target Expansion */}
          {targets.length > 0 && (
            <div className="relative group">
              <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-emerald-500 border-2 border-[#0b0f19] shadow-sm" />
              <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Target className="h-3.5 w-3.5 text-emerald-400" />
                    <span>3. Configured & Provider Targets</span>
                  </span>
                </div>
                <div className="flex flex-wrap gap-2 text-xs font-mono">
                  {targets.map((tp, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-emerald-300">
                      TP{idx + 1}: {tp}
                    </span>
                  ))}
                  {signal.metrics?.r2_target && (
                    <span className="px-2 py-0.5 rounded bg-sky-950/40 border border-sky-800/40 text-sky-300">
                      2.0R Benchmark: {signal.metrics.r2_target}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Trade Management & Risk-Free Adjustments */}
          {managementEvents.length > 0 && (
            <div className="relative group">
              <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-amber-500 border-2 border-[#0b0f19] shadow-sm" />
              <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Activity className="h-3.5 w-3.5 text-amber-400" />
                    <span>4. Dynamic Trade Management Updates</span>
                  </span>
                </div>
                <div className="space-y-1 font-mono text-xs text-amber-300">
                  {managementEvents.map((ev, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <ArrowRight className="h-3 w-3 text-amber-500" />
                      <span>{ev.action || 'MANAGEMENT_EVENT'}: {ev.text || JSON.stringify(ev)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Step 5: Provider Outcomes */}
          {providerOutcomes.length > 0 && (
            <div className="relative group">
              <div className="absolute -left-6 top-1 h-3.5 w-3.5 rounded-full bg-purple-500 border-2 border-[#0b0f19] shadow-sm" />
              <div className="p-3 bg-slate-900/90 rounded-lg border border-slate-800 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Zap className="h-3.5 w-3.5 text-purple-400" />
                    <span>5. Provider Claimed Updates</span>
                  </span>
                </div>
                <div className="space-y-1 font-mono text-xs text-purple-300">
                  {providerOutcomes.map((out, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <CheckCircle2 className="h-3 w-3 text-purple-400" />
                      <span>{out.text || `${out.pips} pips reported`}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 2. Dual Outcome Audit: Provider Reported vs Simulated Execution */}
      <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-sky-400" />
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Dual Outcome Verification Matrix
            </span>
          </div>
          <span className="text-[10px] text-slate-400">Zero Lookahead Simulation</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          {/* Provider Claimed Outcome */}
          <div className="p-4 bg-slate-900/80 rounded-xl border border-purple-500/30 space-y-3">
            <div className="flex items-center justify-between text-purple-400 font-bold border-b border-purple-500/20 pb-2">
              <span>Provider Claimed Outcome</span>
              <span className="text-[10px] bg-purple-950/60 px-2 py-0.5 rounded text-purple-300">
                Telegram Group
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Claimed Status:</span>
                <span className="text-purple-300 font-bold">{providerClaimedStatus || 'None Broadcasted'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Claimed Pips:</span>
                <span className="text-purple-300 font-bold">
                  {providerClaimedPips ? `+${providerClaimedPips} pips` : '—'}
                </span>
              </div>
              <div className="text-[10px] text-slate-500 mt-2">
                * Note: Telegram provider outcomes frequently cherry-pick maximum intraday spikes without accounting for strict stop-loss mechanics.
              </div>
            </div>
          </div>

          {/* Market-Calculated Simulation Outcome */}
          <div className="p-4 bg-slate-900/80 rounded-xl border border-sky-500/30 space-y-3">
            <div className="flex items-center justify-between text-sky-400 font-bold border-b border-sky-500/20 pb-2">
              <span>Market-Calculated Paper Trade</span>
              <span className="text-[10px] bg-sky-950/60 px-2 py-0.5 rounded text-sky-300">
                Deterministic Simulator
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-400">Trade Status:</span>
                <span className={`font-bold ${
                  trade?.status === 'CLOSED_TP'
                    ? 'text-emerald-400'
                    : trade?.status === 'CLOSED_SL'
                    ? 'text-rose-400'
                    : 'text-sky-300'
                }`}>
                  {trade?.status || 'NO_PAPER_TRADE'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Realized R:</span>
                <span className={`font-bold ${
                  (trade?.realized_r_multiple ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                  {trade && trade.status.startsWith('CLOSED')
                    ? `${trade.realized_r_multiple >= 0 ? '+' : ''}${trade.realized_r_multiple.toFixed(2)}R`
                    : 'Active / Pending'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Realized PnL:</span>
                <span className="text-slate-200 font-bold">
                  {trade?.realized_pnl_usd !== undefined ? `$${trade.realized_pnl_usd.toFixed(2)}` : '—'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Exit Price & Reason:</span>
                <span className="text-slate-200 font-bold">
                  {trade?.exit_price ? `${trade.exit_price} (${trade.exit_reason})` : '—'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
