import React, { useState } from 'react';
import {
  Copy,
  Check,
  Edit3,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HelpCircle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import type { TradePlanItem, ValueProvenance } from '../types';

interface TradePlanCardProps {
  plan: TradePlanItem;
  onEdit?: (plan: TradePlanItem) => void;
  onToggleExecuted?: (plan: TradePlanItem) => void;
}

export const TradePlanCard: React.FC<TradePlanCardProps> = ({ plan, onEdit, onToggleExecuted }) => {
  const [copied, setCopied] = useState(false);
  const [isCalcExpanded, setIsCalcExpanded] = useState(false);

  const isBuy = plan.side.toUpperCase() === 'BUY';
  const isSell = plan.side.toUpperCase() === 'SELL';
  const isReady = plan.plan_status === 'READY';
  const isWaitingSL = plan.plan_status === 'WAITING_FOR_SL';
  const isIncomplete = plan.plan_status === 'INCOMPLETE';
  const isNotReady = plan.plan_status === 'NOT_READY';
  const isExecuted = plan.is_manually_executed;

  const precision = plan.symbol.includes('JPY') ? 3 : plan.symbol === 'XAUUSD' || plan.symbol === 'GOLD' ? 2 : 5;
  const formatPrice = (val?: number | null) => {
    if (val === undefined || val === null) return '—';
    return val.toFixed(precision);
  };

  const getProvenanceBadge = (prov?: ValueProvenance) => {
    if (prov === 'USER_MODIFIED') {
      return (
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 font-bold uppercase tracking-wider">
          USER MODIFIED
        </span>
      );
    }
    if (prov === 'SYSTEM_CALCULATED') {
      return (
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30 font-bold uppercase tracking-wider">
          SYSTEM CALCULATED
        </span>
      );
    }
    return (
      <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-bold uppercase tracking-wider">
        TELEGRAM
      </span>
    );
  };

  const handleCopyPlan = () => {
    const textToCopy = `📋 TRADE PLAN: ${plan.symbol} ${plan.side}
• Entry: ${plan.entry_zone_low && plan.entry_zone_high && plan.entry_zone_low !== plan.entry_zone_high ? `${plan.entry_zone_low} - ${plan.entry_zone_high} (Ref: ${plan.entry_price})` : plan.entry_price}
• Stop Loss: ${plan.stop_loss ?? 'None'}
• Target 1: ${plan.tp1 ?? 'None'}
• Target 2: ${plan.tp2 ?? 'None'}
• Target 3: ${plan.tp3 ?? 'None'}
• Position Size: ${plan.calculated_lot_size} Lots
• Max Risk: ₹${plan.monetary_risk_inr.toFixed(2)} ($${plan.monetary_risk_usd.toFixed(2)})`;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const hasZone = plan.entry_zone_low && plan.entry_zone_high && plan.entry_zone_low !== plan.entry_zone_high;
  const entryDisplay = hasZone
    ? `${formatPrice(plan.entry_zone_low)} – ${formatPrice(plan.entry_zone_high)}`
    : formatPrice(plan.entry_price);

  return (
    <div className={`bg-[#111726] border ${
      isExecuted
        ? 'border-emerald-500/50 ring-1 ring-emerald-500/30'
        : isReady
        ? 'border-[#1e293b] hover:border-sky-500/50'
        : isWaitingSL
        ? 'border-amber-500/40'
        : 'border-slate-800'
    } rounded-xl overflow-hidden shadow-lg transition-all font-mono text-xs flex flex-col justify-between`}>
      {/* Header */}
      <div>
        <div className="p-4 bg-slate-900/90 border-b border-[#1e293b] flex items-center justify-between">
          <div>
            <div className="text-base font-extrabold text-white tracking-wider flex items-center gap-2 font-sans">
              <span>{plan.symbol}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-black tracking-wider ${
                isBuy
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : isSell
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                {plan.side}
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-sans mt-0.5">
              {plan.order_type} • Created: {plan.created_at ? new Date(plan.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Just now'}
            </div>
          </div>

          {/* Status Badge */}
          <div>
            <span className={`px-2.5 py-1 rounded text-[11px] font-black tracking-wider flex items-center gap-1.5 ${
              isExecuted
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : isReady
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/40'
                : isWaitingSL
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : isIncomplete
                ? 'bg-slate-800 text-slate-400 border border-slate-700'
                : 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
            }`}>
              {isExecuted && <Check className="h-3.5 w-3.5" />}
              {isReady && !isExecuted && <CheckCircle2 className="h-3.5 w-3.5" />}
              {isWaitingSL && <Clock className="h-3.5 w-3.5 animate-pulse" />}
              {isNotReady && <AlertTriangle className="h-3.5 w-3.5" />}
              {plan.plan_status.replace(/_/g, ' ')}
            </span>
          </div>
        </div>

        {/* Guard Warning notice if NOT READY */}
        {isNotReady && plan.guard_rejection_reason && (
          <div className="px-4 py-2 bg-amber-950/40 border-b border-amber-900/40 text-amber-300 text-[11px] font-sans flex items-start gap-1.5">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
            <span>{plan.guard_rejection_reason}</span>
          </div>
        )}

        {/* Section 1: Entry & Stop Loss */}
        <div className="p-4 border-b border-[#1e293b] space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-sans">{hasZone ? 'Entry Zone' : 'Entry Price'}</span>
              {getProvenanceBadge(plan.entry_provenance)}
            </div>
            <div className="text-right">
              <span className="font-bold text-slate-100 text-sm">{entryDisplay}</span>
              {hasZone && plan.entry_price && (
                <div className="text-[11px] text-sky-400/90 font-mono mt-0.5">
                  Reference: {formatPrice(plan.entry_price)}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-sans">Stop Loss</span>
              {getProvenanceBadge(plan.sl_provenance)}
            </div>
            <span className={`font-bold text-sm ${plan.stop_loss ? 'text-rose-400' : 'text-slate-500'}`}>
              {formatPrice(plan.stop_loss)}
            </span>
          </div>
        </div>

        {/* Section 2: Multi-Target Take Profits */}
        <div className="p-4 border-b border-[#1e293b] space-y-2 bg-slate-950/40">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-sans font-bold mb-1">
            Take Profit Targets (R-Multiples)
          </div>

          {/* TP1 */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-300 font-sans">TP1 (1.0R)</span>
              {getProvenanceBadge(plan.tp1_provenance)}
            </div>
            <span className="font-bold text-emerald-400">{formatPrice(plan.tp1)}</span>
          </div>

          {/* TP2 */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-300 font-sans">TP2 (2.0R)</span>
              {getProvenanceBadge(plan.tp2_provenance)}
            </div>
            <span className="font-bold text-emerald-400">{formatPrice(plan.tp2)}</span>
          </div>

          {/* TP3 */}
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-300 font-sans">TP3 (3.0R)</span>
              {getProvenanceBadge(plan.tp3_provenance)}
            </div>
            <span className="font-bold text-emerald-400">{formatPrice(plan.tp3)}</span>
          </div>
        </div>

        {/* Section 3: Position Sizing & Monetary Risk */}
        <div className="p-4 border-b border-[#1e293b] space-y-2 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-sans">Calculated Position Size</span>
            <span className="font-extrabold text-sky-400 text-sm">
              {plan.calculated_lot_size > 0 ? `${plan.calculated_lot_size} Lots` : '0.00 (Exceeds Risk)'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-sans">Monetary Risk (INR)</span>
            <span className="font-bold text-slate-200">
              ₹{plan.monetary_risk_inr.toFixed(2)}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-sans">Monetary Risk (USD)</span>
            <span className="text-slate-300 font-medium">
              ${plan.monetary_risk_usd.toFixed(2)}
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-800">
            <span>Risk Distance: {plan.risk_distance_points ?? '--'} pts</span>
            <span>R:R Benchmark: 1 : {plan.reward_risk_ratio_tp2 ?? '2.0'}</span>
          </div>
        </div>
      </div>

      {/* Footer & Actions */}
      <div>
        {/* Action Buttons */}
        <div className="p-3 bg-slate-900 border-b border-[#1e293b] flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyPlan}
            className="flex-1 py-2 px-3 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-sans font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer shadow-sm"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            <span>{copied ? 'Copied to Clipboard!' : 'Copy Trade Plan'}</span>
          </button>

          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(plan)}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
              title="Manually Override Entry / SL / TP"
            >
              <Edit3 className="h-4 w-4" />
            </button>
          )}

          {onToggleExecuted && (
            <button
              type="button"
              onClick={() => onToggleExecuted(plan)}
              className={`px-3 py-2 rounded-lg text-xs font-sans font-semibold transition-colors cursor-pointer flex items-center gap-1 ${
                isExecuted
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
              }`}
              title="Track that you manually placed this trade on your broker terminal"
            >
              <Check className="h-3.5 w-3.5" />
              <span>{isExecuted ? 'Executed' : 'Mark Executed'}</span>
            </button>
          )}
        </div>

        {/* Expandable Risk & Sizing Transparency */}
        <div className="bg-[#0b0f19]">
          <button
            type="button"
            onClick={() => setIsCalcExpanded(!isCalcExpanded)}
            className="w-full px-4 py-2 flex items-center justify-between text-slate-400 hover:text-slate-200 text-[11px] font-sans transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-1.5">
              <HelpCircle className="h-3.5 w-3.5 text-sky-400" />
              <span>Risk & Sizing Transparency</span>
            </div>
            {isCalcExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>

          {isCalcExpanded && (
            <div className="p-4 pt-2 border-t border-slate-800 text-[11px] font-sans text-slate-300 space-y-2 bg-slate-950/60">
              <div className="grid grid-cols-2 gap-2 text-slate-400 font-mono text-[10px]">
                <div>• Account Balance: ₹{(plan.calculation_details?.current_balance_inr ?? 50000).toLocaleString()}</div>
                <div>• Configured Risk: {plan.calculation_details?.risk_per_trade_pct ?? 1.0}%</div>
                <div>• Max Risk Limit: ₹{(plan.calculation_details?.max_risk_per_trade_inr ?? 500).toFixed(2)}</div>
                <div>• USD/INR Rate: ₹{(plan.calculation_details?.usd_inr_rate ?? 85.0).toFixed(2)} [MANUAL]</div>
                <div>• Contract Size: {plan.calculation_details?.contract_size ?? 100} oz</div>
                <div>• Risk Distance: {plan.risk_distance_points ?? '--'} pts</div>
              </div>

              <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
                Formula: Lots = (Max Risk ₹500 ÷ 85.00) ÷ (Risk Distance × Contract Size 100). Strictly rounded DOWN to 0.01 step.
              </div>

              {plan.original_telegram_values && (
                <div className="p-2 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400">
                  <span className="font-bold text-slate-200 block mb-0.5">Original Telegram Record (Unaltered):</span>
                  {plan.raw_message}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
