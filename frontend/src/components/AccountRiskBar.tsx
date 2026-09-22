import React from 'react';
import { IndianRupee, PieChart, AlertCircle, RefreshCw } from 'lucide-react';
import type { AccountRiskStatusV1 } from '../types';

interface AccountRiskBarProps {
  status: AccountRiskStatusV1 | null;
  loading?: boolean;
  onRefresh?: () => void;
}

export const AccountRiskBar: React.FC<AccountRiskBarProps> = ({ status, loading, onRefresh }) => {
  if (!status) return null;

  const currentBal = status.current_balance;
  const maxRiskPerTrade = status.max_risk_per_trade_inr;
  const dailyRiskLimit = status.daily_risk_limit_inr;
  const dailyRiskUsed = status.daily_risk_used_inr;
  const dailyRiskRemaining = status.daily_risk_remaining_inr;
  const openTrades = status.open_trades_count;
  const maxOpenTrades = status.max_open_trades;
  const usdInrRate = status.manual_usd_inr_rate;

  const isDailyRiskNearLimit = dailyRiskRemaining <= 0;
  const isOpenTradesAtLimit = openTrades >= maxOpenTrades;

  return (
    <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-4 shadow-sm font-mono text-xs">
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Account Balance & Per-Trade Risk */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <IndianRupee className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Account Balance</div>
              <div className="text-sm font-bold text-slate-100">
                ₹{currentBal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          <div className="border-l border-slate-800 pl-6">
            <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Risk Per Trade ({status.risk_percent}%)</div>
            <div className="text-sm font-bold text-sky-400">
              Max ₹{maxRiskPerTrade.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        {/* Daily Risk Budget & Open Trades */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className={`p-2 rounded-lg ${isDailyRiskNearLimit ? 'bg-rose-500/10 text-rose-400' : 'bg-sky-500/10 text-sky-400'}`}>
              <PieChart className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Daily Risk Budget (3%)</div>
              <div className="text-xs font-bold text-slate-200">
                ₹{dailyRiskUsed.toFixed(2)} / ₹{dailyRiskLimit.toFixed(2)}
                <span className="text-[10px] text-slate-400 ml-1.5 font-normal">
                  (₹{dailyRiskRemaining.toFixed(2)} left)
                </span>
              </div>
            </div>
          </div>

          <div className="border-l border-slate-800 pl-6">
            <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold">Tracked Open Trades</div>
            <div className={`text-sm font-bold ${isOpenTradesAtLimit ? 'text-amber-400' : 'text-slate-200'}`}>
              {openTrades} / {maxOpenTrades} limit
            </div>
          </div>

          {/* USD/INR Manual Conversion Rate */}
          <div className="border-l border-slate-800 pl-6 hidden md:block">
            <div className="text-[10px] text-slate-400 uppercase font-sans font-semibold flex items-center gap-1">
              <span>USD/INR</span>
              <span className="px-1 py-0.2 rounded bg-slate-800 text-[9px] text-amber-400 font-bold">MANUAL</span>
            </div>
            <div className="text-xs font-bold text-slate-300">
              ₹{usdInrRate.toFixed(2)}
            </div>
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Refresh Account Status"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Warning Banners if Risk Guards triggered */}
      {(isDailyRiskNearLimit || isOpenTradesAtLimit) && (
        <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center gap-2 text-[11px] font-sans text-amber-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>
            {isDailyRiskNearLimit && 'Daily risk limit reached. New incoming signals will be analyzed but marked NOT READY.'}
            {isDailyRiskNearLimit && isOpenTradesAtLimit && ' • '}
            {isOpenTradesAtLimit && 'Maximum 3 open trades reached. Close or unmark existing trades to enable new plans.'}
          </span>
        </div>
      )}
    </div>
  );
};
