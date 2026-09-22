import React, { useState } from 'react';
import {
  HelpCircle,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  TrendingUp
} from 'lucide-react';
import type { SignalItem } from '../types';

export interface SignalDecisionCardProps {
  signal: SignalItem;
  className?: string;
  onInspect?: (signal: SignalItem) => void;
}

export const SignalDecisionCard: React.FC<SignalDecisionCardProps> = ({
  signal,
  className = '',
  onInspect,
}) => {
  const [isWhyExpanded, setIsWhyExpanded] = useState(false);

  const m = signal.metrics;
  const symbol = signal.symbol || 'UNKNOWN';
  const side = signal.side || 'UNKNOWN';
  const isBuy = side === 'BUY';
  const isSell = side === 'SELL';
  const isValid = signal.validation_status === 'VALID';
  const isSkipped = signal.validation_status.startsWith('SKIPPED');

  const entry = signal.entry_price ?? 0;
  const sl = signal.provider_sl ?? m?.effective_sl;
  const providerTps = signal.provider_tps || [];
  const primaryProviderTp = providerTps.length > 0 ? providerTps[0] : null;

  // Formatting precision
  const precision = symbol.includes('JPY') ? 3 : symbol === 'XAUUSD' ? 2 : symbol.includes('USD') ? 5 : 2;
  const formatPrice = (val?: number | null) => {
    if (val === undefined || val === null) return '—';
    return val.toFixed(precision);
  };

  // Risk distance
  const riskDist = m?.risk_price_diff ?? (sl !== undefined && sl !== null && entry ? Math.abs(entry - sl) : null);

  // Targets
  const r1 = m?.r1_target ?? (riskDist && entry ? (isBuy ? entry + riskDist * 1 : entry - riskDist * 1) : null);
  const r1_5 = m?.r1_5_target ?? (riskDist && entry ? (isBuy ? entry + riskDist * 1.5 : entry - riskDist * 1.5) : null);
  const r2 = m?.r2_target ?? (riskDist && entry ? (isBuy ? entry + riskDist * 2 : entry - riskDist * 2) : null);
  const r3 = m?.r3_target ?? (riskDist && entry ? (isBuy ? entry + riskDist * 3 : entry - riskDist * 3) : null);

  // Selected TP determination
  let selectedTp: number | null = null;
  let tpSource: 'PROVIDER' | 'CALCULATED' | 'NONE' = 'NONE';
  let rrDisplay = '1 : 2';

  if (primaryProviderTp) {
    selectedTp = primaryProviderTp;
    tpSource = 'PROVIDER';
    if (riskDist && riskDist > 0) {
      const pRrr = isBuy ? (primaryProviderTp - entry) / riskDist : (entry - primaryProviderTp) / riskDist;
      rrDisplay = `1 : ${pRrr.toFixed(1)}`;
    }
  } else if (r2) {
    selectedTp = r2;
    tpSource = 'CALCULATED';
    rrDisplay = '1 : 2';
  }

  // Determine status label
  const statusLabel = isValid
    ? 'PAPER TRADE'
    : isSkipped
    ? 'SKIPPED (NO SL)'
    : 'REJECTED';

  return (
    <div className={`bg-[#111726] border border-[#1e293b] hover:border-sky-500/40 rounded-xl overflow-hidden shadow-lg transition-all font-mono text-xs ${className}`}>
      {/* Header */}
      <div className="p-4 bg-slate-900/90 border-b border-[#1e293b] flex items-center justify-between">
        <div>
          <div className="text-base font-extrabold text-white tracking-wider flex items-center gap-2 font-sans">
            <span>{symbol}</span>
            {isValid && (
              <span className="flex h-2 w-2 relative" title="Simulated active trade">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            )}
          </div>
          <div className="text-[10px] text-slate-400 font-sans mt-0.5">
            Telegram Signal • {new Date(signal.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`px-3 py-1 rounded-md text-xs font-black tracking-wider ${
              isBuy
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                : isSell
                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}
          >
            {side}
          </span>
        </div>
      </div>

      {/* Section 1: Entry, Stop Loss, Provider TP */}
      <div className="p-4 border-b border-[#1e293b] space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Entry</span>
          <span className="font-bold text-slate-100">
            {signal.entry_zone_low !== undefined && signal.entry_zone_high !== undefined && signal.entry_zone_low !== null && signal.entry_zone_high !== null
              ? `${formatPrice(signal.entry_zone_low)} - ${formatPrice(signal.entry_zone_high)}`
              : formatPrice(entry)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Stop Loss</span>
          <span className={`font-bold ${sl !== undefined && sl !== null ? 'text-rose-400' : 'text-slate-500'}`}>
            {formatPrice(sl)}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Provider TP</span>
          <span className="text-slate-300">
            {providerTps.length > 0 ? providerTps.map((tp) => formatPrice(tp)).join(', ') : '—'}
          </span>
        </div>
      </div>

      {/* Section 2: Risk & R-Multiples */}
      <div className="p-4 border-b border-[#1e293b] space-y-2 bg-slate-950/40">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Risk Distance</span>
          <span className="font-bold text-slate-200">
            {riskDist !== null ? `${riskDist.toFixed(precision)} (${m?.risk_pips ?? '--'} pips)` : '—'}
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-300">
          <span className="text-slate-500">1R TP</span>
          <span className="text-slate-300">{formatPrice(r1)}</span>
        </div>
        <div className="flex items-center justify-between text-slate-300">
          <span className="text-slate-500">1.5R TP</span>
          <span className="text-slate-300">{formatPrice(r1_5)}</span>
        </div>
        <div className="flex items-center justify-between font-bold text-emerald-400">
          <span className="text-emerald-400/80">2R TP (Default)</span>
          <span>{formatPrice(r2)}</span>
        </div>
        <div className="flex items-center justify-between text-slate-300">
          <span className="text-slate-500">3R TP</span>
          <span className="text-slate-300">{formatPrice(r3)}</span>
        </div>
      </div>

      {/* Section 3: Decision & Execution Details */}
      <div className="p-4 border-b border-[#1e293b] space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Selected TP</span>
          <span className="font-bold text-emerald-400">{formatPrice(selectedTp)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">Risk / Reward</span>
          <span className="font-bold text-sky-400">{rrDisplay}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400">TP Source</span>
          <span className="text-slate-200 font-semibold">{tpSource}</span>
        </div>
      </div>

      {/* Section 4: Status Footer */}
      <div className="px-4 py-3 bg-slate-900/60 flex items-center justify-between border-b border-[#1e293b]">
        <span className="text-slate-400 uppercase text-[10px] font-bold tracking-wider">Decision Status</span>
        <span
          className={`px-2.5 py-1 rounded text-[11px] font-black tracking-wider flex items-center gap-1.5 ${
            isValid
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
              : isSkipped
              ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
              : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
          }`}
        >
          {isValid && <CheckCircle2 className="h-3.5 w-3.5" />}
          {!isValid && !isSkipped && <XCircle className="h-3.5 w-3.5" />}
          {isSkipped && <AlertTriangle className="h-3.5 w-3.5" />}
          {statusLabel}
        </span>
      </div>

      {/* Section 5: Expandable "Why?" Reason & Logic */}
      <div className="bg-[#0b0f19]">
        <button
          type="button"
          onClick={() => setIsWhyExpanded(!isWhyExpanded)}
          className="w-full px-4 py-2.5 flex items-center justify-between text-sky-400 hover:text-sky-300 hover:bg-slate-800/40 text-xs font-semibold font-sans transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-1.5">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Why this decision?</span>
          </div>
          {isWhyExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {isWhyExpanded && (
          <div className="p-4 pt-2 border-t border-slate-800 text-[11px] space-y-3 font-sans text-slate-300 leading-relaxed bg-slate-950/60">
            {/* 1. Why Accepted / Validated */}
            <div>
              <div className="font-bold text-slate-100 flex items-center gap-1 mb-0.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Signal Validation Reason</span>
              </div>
              <p className="text-slate-400">
                {isValid
                  ? `Signal was accepted because symbol (${symbol}), side (${side}), entry (${formatPrice(entry)}), and stop loss (${formatPrice(sl)}) were successfully extracted with directional geometry verified (${side === 'BUY' ? 'SL is below entry' : 'SL is above entry'}).`
                  : `Signal was ${signal.validation_status.toLowerCase()}: ${signal.rejection_reason || 'Incomplete mandatory levels'}.`}
              </p>
            </div>

            {/* 2. How SL was obtained */}
            <div>
              <div className="font-bold text-slate-100 mb-0.5">How Stop Loss Was Obtained</div>
              <p className="text-slate-400">
                {sl !== undefined && sl !== null
                  ? `Extracted directly from Telegram message level ${formatPrice(sl)} (Source: ${m?.sl_source || 'PROVIDER'}). Zero-assumption rule enforced (SL is never fabricated).`
                  : 'No Stop Loss was present in message. Signal rejected from live paper trade execution under strict zero-assumption policy.'}
              </p>
            </div>

            {/* 3. How Risk was calculated */}
            <div>
              <div className="font-bold text-slate-100 mb-0.5">How Risk Was Calculated</div>
              <p className="text-slate-400 font-mono text-[10px]">
                {riskDist !== null
                  ? `Risk Distance = |Entry (${formatPrice(entry)}) - SL (${formatPrice(sl)})| = ${riskDist.toFixed(precision)} (${m?.risk_pips ?? '--'} pips).`
                  : 'N/A (Missing valid entry or SL).'}
              </p>
            </div>

            {/* 4. How TP & Selected TP were obtained */}
            <div>
              <div className="font-bold text-slate-100 mb-0.5">Why Selected TP Was Chosen</div>
              <p className="text-slate-400">
                {tpSource === 'PROVIDER'
                  ? `Provider supplied explicit TP ${formatPrice(selectedTp)}, which met or exceeded the minimum Risk/Reward threshold (1:${m?.provider_tp_rrrs ? Object.values(m.provider_tp_rrrs)[0] : '1.5+'}).`
                  : tpSource === 'CALCULATED'
                  ? `Provider did not supply a single definitive TP; system deterministically calculated standard 2.0R target level (${formatPrice(selectedTp)}) using formula: Entry ${isBuy ? '+' : '-'} (Risk × 2.0).`
                  : 'No TP target could be determined.'}
              </p>
            </div>

            {/* 5. Warnings & Uncertainty Disclaimer */}
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-[10px] text-slate-400">
              <span className="font-bold text-amber-400 block mb-0.5">Simulation & Risk Notice:</span>
              This calculation is strictly for simulated paper-trading telemetry. Historical mathematical expectancy does not imply certainty regarding individual trade outcomes.
            </div>

            {/* Optional inspect button */}
            {onInspect && (
              <div className="pt-1 text-right">
                <button
                  type="button"
                  onClick={() => onInspect(signal)}
                  className="text-xs text-sky-400 hover:text-sky-300 font-semibold inline-flex items-center gap-1 cursor-pointer"
                >
                  <TrendingUp className="h-3 w-3" />
                  View Full Audit Telemetry →
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

