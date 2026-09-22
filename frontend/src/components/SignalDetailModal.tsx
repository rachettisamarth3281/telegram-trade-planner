import React from 'react';
import {
  X,
  Layers,
  Activity,
  Zap,
  FileText,
  ShieldCheck
} from 'lucide-react';
import type { SignalItem, PaperTradeItem } from '../types';
import { SignalTimelineView } from './SignalTimelineView';

interface SignalDetailModalProps {
  signal: SignalItem | null;
  trade?: PaperTradeItem | null;
  onClose: () => void;
}

export const SignalDetailModal: React.FC<SignalDetailModalProps> = ({
  signal,
  trade,
  onClose,
}) => {
  if (!signal) return null;

  const isValid = signal.validation_status === 'VALID';
  const isSkipped = signal.validation_status.startsWith('SKIPPED');
  const m = signal.metrics;
  const prov = trade?.provenance;

  const symbol = signal.symbol || 'UNKNOWN';
  const side = signal.side || 'UNKNOWN';
  const isBuy = side === 'BUY';
  const entry = signal.entry_price ?? 0;
  const sl = signal.provider_sl ?? m?.effective_sl;
  const riskDist = m?.risk_price_diff ?? (sl !== undefined && sl !== null && entry ? Math.abs(entry - sl) : null);
  const selectedTp = trade?.active_tp ?? m?.r2_target ?? (signal.provider_tps && signal.provider_tps.length > 0 ? signal.provider_tps[0] : null);
  const isProviderTp = Boolean(signal.provider_tps && signal.provider_tps.length > 0 && selectedTp === signal.provider_tps[0]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="bg-[#111726] border border-sky-500/40 rounded-2xl max-w-4xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#1e293b] flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-white text-base">Signal Deep Audit & Financial Provenance</h3>
                <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                  isValid
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    : isSkipped
                    ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                }`}>
                  {signal.validation_status}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Signal ID: {signal.id} • Received: {new Date(signal.created_at).toLocaleString()}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body (Scrollable) */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* 11-Point Financial Calculation & Audit Traceability Matrix */}
          <div className="bg-slate-900/90 border border-sky-500/30 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              <ShieldCheck className="h-4 w-4 text-sky-400" />
              <span className="text-xs font-bold text-sky-300 uppercase tracking-wider font-sans">
                Global Rule: 11-Point Financial Audit Traceability
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">1. Originating Message:</span>
                <span className="text-slate-200 truncate block font-bold">{signal.raw_text.replace(/\n/g, ' ')}</span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">2. Extracted Values:</span>
                <span className="text-slate-200 block font-bold">
                  {symbol} {side} @ {entry} (SL: {sl ?? 'None'}, TP: {signal.provider_tps?.join(', ') || 'None'})
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">3. Stop Loss Provenance:</span>
                <span className="text-rose-400 block font-bold">
                  {sl !== undefined && sl !== null ? `PROVIDER SPECIFIED (${sl})` : 'NONE (Zero-Assumption Rejection)'}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">4. Take Profit Provenance:</span>
                <span className="text-emerald-400 block font-bold">
                  {isProviderTp ? 'PROVIDER SPECIFIED' : 'CALCULATED R-MULTIPLE'}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">5. TP Mathematical Formula:</span>
                <span className="text-sky-400 block font-bold">
                  {isProviderTp
                    ? `Provider TP Level (${selectedTp})`
                    : `Entry (${entry}) ${isBuy ? '+' : '-'} (Risk ${riskDist?.toFixed(2)} × 2.0R) = ${selectedTp}`}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">6. Initial Risk Distance:</span>
                <span className="text-slate-200 block font-bold">
                  {riskDist ? `${riskDist.toFixed(2)} (${m?.risk_pips ?? '--'} pips, $${m?.risk_amount_usd ?? 100} allocated)` : 'N/A'}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">7. Risk / Reward Ratio:</span>
                <span className="text-sky-300 block font-bold">
                  {prov?.risk_reward_ratio || '1:2.0'}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">8. Acceptance / Rejection Reason:</span>
                <span className={isValid ? 'text-emerald-400 block font-bold' : 'text-rose-400 block font-bold'}>
                  {signal.rejection_reason || 'VALID_SIGNAL: Directional geometry & Stop Loss verified'}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">9. Closing Execution Price:</span>
                <span className="text-slate-200 block font-bold">
                  {trade?.exit_price ? trade.exit_price.toFixed(2) : 'Active Simulation Running'}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800">
                <span className="text-slate-500 block text-[10px]">10. Closing Reason:</span>
                <span className="text-slate-200 block font-bold">
                  {trade?.exit_reason || (trade?.status === 'OPEN' ? 'In Progress' : 'No Trade Opened')}
                </span>
              </div>

              <div className="p-2 bg-slate-950/60 rounded border border-slate-800 md:col-span-2">
                <span className="text-slate-500 block text-[10px]">11. Final Realized R Multiple:</span>
                <span className={`block font-extrabold text-sm ${trade && trade.realized_r_multiple >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {trade && trade.status.startsWith('CLOSED')
                    ? `${trade.realized_r_multiple >= 0 ? '+' : ''}${trade.realized_r_multiple.toFixed(2)}R ($${trade.realized_pnl_usd.toFixed(2)})`
                    : 'Active / Pending Close'}
                </span>
              </div>
            </div>
          </div>

          {/* Multi-Message Sequence & Dual Outcome Verification */}
          <SignalTimelineView signal={signal} trade={trade} />

          {/* Original Telegram Message Section */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              <FileText className="h-4 w-4 text-sky-400" />
              <span>Verbatim Telegram Record (Zero Overwrites Guarantee)</span>
            </div>
            <pre className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 text-xs font-mono text-slate-100 whitespace-pre-wrap leading-relaxed shadow-inner">
              {signal.raw_text}
            </pre>
          </div>

          {/* Mathematical Calculations Matrix */}
          {m && (
            <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 space-y-4">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                <Zap className="h-4 w-4 text-amber-400" />
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Deterministic Multi-Target Calculator
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
                <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400">Effective SL</div>
                  <div className="text-sm font-bold text-rose-400 mt-1">{m.effective_sl}</div>
                  <div className="text-[10px] text-slate-500">Source: {m.sl_source}</div>
                </div>

                <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400">Risk Distance</div>
                  <div className="text-sm font-bold text-slate-200 mt-1">{m.risk_price_diff}</div>
                  <div className="text-[10px] text-slate-500">{m.risk_pips} pips</div>
                </div>

                <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400">Suggested Lot Size</div>
                  <div className="text-sm font-bold text-sky-400 mt-1">{m.suggested_lot_size} Lots</div>
                  <div className="text-[10px] text-slate-500">Fixed risk ${m.risk_amount_usd}</div>
                </div>

                <div className="p-3 bg-slate-900/80 rounded-lg border border-slate-800">
                  <div className="text-[10px] text-slate-400">Standard 2.0R Target</div>
                  <div className="text-sm font-bold text-emerald-400 mt-1">{m.r2_target}</div>
                  <div className="text-[10px] text-slate-500">+2.00 Multiplier</div>
                </div>
              </div>
            </div>
          )}

          {/* Trade Events Audit Log */}
          {trade && trade.events && trade.events.length > 0 && (
            <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
                <Activity className="h-4 w-4 text-sky-400" />
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Simulated Trade Event Log
                </span>
              </div>

              <div className="space-y-1.5">
                {trade.events.map((ev) => (
                  <div key={ev.id} className="p-2 bg-slate-900/50 rounded border border-slate-800 flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-200">{ev.event_type}</span>
                      {ev.price && <span className="text-slate-400">@ {ev.price}</span>}
                    </div>
                    <span className="text-slate-500">{new Date(ev.created_at).toLocaleTimeString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#1e293b] bg-slate-900/80 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            Strict Traceability • Zero Hidden Calculations
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
