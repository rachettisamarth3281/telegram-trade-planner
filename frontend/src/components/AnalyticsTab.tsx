import React, { useEffect, useState } from 'react';
import {
  TrendingUp,
  BarChart3,
  PieChart,
  Calendar,
  Clock,
  Layers,
  ShieldCheck,
  AlertOctagon
} from 'lucide-react';
import type { CompleteAnalyticsReport, EquityCurveData, PaperTradeItem } from '../types';
import { fetchCompleteAnalyticsReport, fetchEquityCurve, fetchTrades } from '../lib/api';

export const AnalyticsTab: React.FC = () => {
  const [report, setReport] = useState<CompleteAnalyticsReport | null>(null);
  const [equity, setEquity] = useState<EquityCurveData | null>(null);
  const [allTrades, setAllTrades] = useState<PaperTradeItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [repData, eqData, trdData] = await Promise.all([
          fetchCompleteAnalyticsReport(),
          fetchEquityCurve(),
          fetchTrades()
        ]);
        setReport(repData);
        setEquity(eqData);
        setAllTrades(trdData);
      } catch (e) {
        console.error('Failed to load complete analytics', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mr-3" />
        Calculating statistical metrics & generating chart data...
      </div>
    );
  }

  const p = report?.performance;
  const t = report?.trades;
  const s = report?.signals;
  const comp = report?.provider_comparison;

  // Closed trades list
  const closedTrades = allTrades.filter((tr) => tr.status.startsWith('CLOSED'));

  // Calculate R Distribution Buckets
  const rBuckets = [
    { label: '< -1.0R', count: 0, color: 'bg-rose-700' },
    { label: '-1.0R (SL)', count: 0, color: 'bg-rose-500' },
    { label: '-0.9R to 0R', count: 0, color: 'bg-rose-400/70' },
    { label: '0R to +1.0R', count: 0, color: 'bg-sky-400' },
    { label: '+1.0R to +1.9R', count: 0, color: 'bg-emerald-400/80' },
    { label: '+2.0R+ (TP)', count: 0, color: 'bg-emerald-500' },
  ];

  closedTrades.forEach((tr) => {
    const r = tr.realized_r_multiple;
    if (r < -1.05) rBuckets[0].count++;
    else if (r >= -1.05 && r <= -0.95) rBuckets[1].count++;
    else if (r > -0.95 && r < 0) rBuckets[2].count++;
    else if (r >= 0 && r < 1.0) rBuckets[3].count++;
    else if (r >= 1.0 && r < 2.0) rBuckets[4].count++;
    else if (r >= 2.0) rBuckets[5].count++;
  });

  const maxRBucketCount = Math.max(...rBuckets.map((b) => b.count), 1);

  // Invalid Reasons Distribution
  const invalidReasons = s?.invalid_signal_reasons || {};
  const invalidReasonsList = Object.entries(invalidReasons).map(([reason, count]) => ({
    reason,
    count
  })).sort((a, b) => b.count - a.count);
  const maxReasonCount = Math.max(...invalidReasonsList.map((r) => r.count), 1);

  // Daily R
  const dailyData = report?.trades_by_date || [];
  const maxDailyR = Math.max(...dailyData.map((d) => Math.abs(d.total_r)), 1);

  // Hourly Distribution (0 to 23)
  const hourlyData = report?.trades_by_hour || [];
  const maxHourlyCount = Math.max(...hourlyData.map((h) => h.trades_count), 1);

  return (
    <div className="space-y-6">
      {/* Objective Analytics Notice Banner */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="font-bold text-white text-sm">Objective Statistical Performance Telemetry</h2>
            <p className="text-xs text-slate-400">
              Pure statistical reporting from forward-simulated paper trades without lookahead bias.
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-4 text-xs font-mono">
          <div className="text-right">
            <div className="text-slate-400">Max DD (R)</div>
            <div className="font-bold text-rose-400">-{p?.max_drawdown_r.toFixed(2)}R</div>
          </div>
          <div className="text-right">
            <div className="text-slate-400">Winning Streak</div>
            <div className="font-bold text-emerald-400">{p?.max_winning_streak} Trades</div>
          </div>
          <div className="text-right">
            <div className="text-slate-400">Losing Streak</div>
            <div className="font-bold text-rose-400">{p?.max_losing_streak} Trades</div>
          </div>
        </div>
      </div>

      {/* KPI Matrix Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Win Rate</span>
          <span className="text-xl font-bold text-white font-mono">{t?.win_rate_pct ?? 0}%</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">{t?.wins}W / {t?.losses}L</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Profit Factor</span>
          <span className="text-xl font-bold text-emerald-400 font-mono">{p?.profit_factor ?? '1.00'}</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Ratio</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Realized R</span>
          <span className={`text-xl font-bold font-mono ${p && p.total_realized_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {p ? `${p.total_realized_r >= 0 ? '+' : ''}${p.total_realized_r.toFixed(2)}R` : '0R'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Net Multiplier</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Avg R / Trade</span>
          <span className="text-xl font-bold text-indigo-400 font-mono">
            {p ? `${p.average_r_per_trade >= 0 ? '+' : ''}${p.average_r_per_trade.toFixed(2)}R` : '0R'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Expectancy</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Avg Win R</span>
          <span className="text-xl font-bold text-emerald-400 font-mono">+{p?.average_win_r.toFixed(2) ?? '0.00'}R</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">On Wins</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Avg Loss R</span>
          <span className="text-xl font-bold text-rose-400 font-mono">-{p?.average_loss_r.toFixed(2) ?? '0.00'}R</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">On Losses</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Avg Risk/Reward</span>
          <span className="text-xl font-bold text-sky-400 font-mono">1:{p?.average_risk_reward.toFixed(2) ?? '2.00'}</span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Target RRR</span>
        </div>
        <div className="bg-[#111726] border border-[#1e293b] p-3.5 rounded-xl">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Net P&L ($)</span>
          <span className={`text-xl font-bold font-mono ${p && p.net_pnl_usd >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {p ? `${p.net_pnl_usd >= 0 ? '+' : ''}$${p.net_pnl_usd.toFixed(2)}` : '$0.00'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-0.5">Simulated</span>
        </div>
      </div>

      {/* Grid: Chart 1 (Cumulative R Curve) & Chart 2 (Daily R) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Chart 1: Cumulative R Curve */}
        <div className="lg:col-span-8 bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-sky-400" />
              <h3 className="font-semibold text-white text-sm">1. Cumulative Realized R Curve</h3>
            </div>
            <span className="text-xs font-mono text-slate-400">
              Total Points: {equity?.curve.length || 0}
            </span>
          </div>

          {equity && equity.curve.length > 0 ? (
            <div className="space-y-2">
              <div className="h-52 bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 flex items-end gap-2 overflow-x-auto">
                {equity.curve.map((pt, i) => {
                  const maxR = Math.max(...equity.curve.map((c) => Math.abs(c.cumulative_r)), 5);
                  const heightPct = Math.min(Math.max((Math.abs(pt.cumulative_r) / maxR) * 100, 8), 100);
                  const isPositive = pt.cumulative_r >= 0;

                  return (
                    <div key={i} className="flex flex-col items-center min-w-[36px] group relative">
                      <div
                        style={{ height: `${heightPct}%` }}
                        className={`w-6 rounded-t transition-all ${
                          isPositive
                            ? 'bg-gradient-to-t from-emerald-600/90 to-emerald-400'
                            : 'bg-gradient-to-t from-rose-600/90 to-rose-400'
                        }`}
                      />
                      <span className="text-[9px] font-mono text-slate-500 mt-1">#{pt.trade_index}</span>

                      {/* Tooltip */}
                      <div className="absolute bottom-full mb-2 hidden group-hover:block bg-slate-900 border border-slate-700 text-[11px] text-slate-200 p-2.5 rounded-lg shadow-xl whitespace-nowrap z-20 font-mono">
                        <div className="font-bold text-white">Trade #{pt.trade_index}: {pt.symbol}</div>
                        <div>Step Realized: {pt.realized_r >= 0 ? `+${pt.realized_r}` : pt.realized_r}R (${pt.realized_pnl})</div>
                        <div className="font-bold text-sky-400 mt-1">Cumulative: {pt.cumulative_r.toFixed(2)}R</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="h-44 flex items-center justify-center border border-dashed border-[#1e293b] rounded-xl text-slate-500 text-xs">
              No closed paper trades available to plot cumulative R curve.
            </div>
          )}
        </div>

        {/* Chart 2: Daily R Bar Chart */}
        <div className="lg:col-span-4 bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-indigo-400" />
              <h3 className="font-semibold text-white text-sm">2. Daily R Performance</h3>
            </div>
            <span className="text-xs text-slate-400">By Date</span>
          </div>

          {dailyData.length === 0 ? (
            <div className="h-44 flex items-center justify-center border border-dashed border-[#1e293b] rounded-xl text-slate-500 text-xs">
              No date data recorded yet.
            </div>
          ) : (
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {dailyData.map((d) => {
                const widthPct = Math.min((Math.abs(d.total_r) / maxDailyR) * 100, 100);
                const isPos = d.total_r >= 0;

                return (
                  <div key={d.date} className="text-xs font-mono">
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>{d.date}</span>
                      <span className={isPos ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                        {isPos ? '+' : ''}{d.total_r.toFixed(2)}R ({d.trades_count} trds)
                      </span>
                    </div>
                    <div className="h-2.5 bg-slate-900 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${Math.max(widthPct, 6)}%` }}
                        className={`h-full rounded-full ${isPos ? 'bg-emerald-400' : 'bg-rose-500'}`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Grid: Chart 3 (Win/Loss), Chart 4 (R Distribution), Chart 5 (Trades by Symbol) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Chart 3: Win / Loss Distribution */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <PieChart className="h-5 w-5 text-emerald-400" />
            <h3 className="font-semibold text-white text-sm">3. Win / Loss Distribution</h3>
          </div>

          <div className="p-4 bg-[#0b0f19] border border-[#1e293b] rounded-xl space-y-4">
            <div className="text-center">
              <div className="text-3xl font-extrabold text-white font-mono">{t?.win_rate_pct ?? 0}%</div>
              <div className="text-xs text-slate-400 mt-1">Observed Win Rate</div>
            </div>

            {/* Segmented Bar */}
            <div className="h-4 bg-slate-900 rounded-full flex overflow-hidden">
              <div
                style={{ width: `${t && t.closed_trades > 0 ? (t.wins / t.closed_trades) * 100 : 0}%` }}
                className="bg-emerald-400 transition-all"
                title={`Wins: ${t?.wins}`}
              />
              <div
                style={{ width: `${t && t.closed_trades > 0 ? (t.breakeven / t.closed_trades) * 100 : 0}%` }}
                className="bg-slate-400 transition-all"
                title={`Breakeven: ${t?.breakeven}`}
              />
              <div
                style={{ width: `${t && t.closed_trades > 0 ? (t.losses / t.closed_trades) * 100 : 0}%` }}
                className="bg-rose-500 transition-all"
                title={`Losses: ${t?.losses}`}
              />
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-2 border-t border-slate-800">
              <div>
                <div className="text-emerald-400 font-bold">{t?.wins ?? 0}</div>
                <div className="text-[10px] text-slate-500">Wins</div>
              </div>
              <div>
                <div className="text-slate-300 font-bold">{t?.breakeven ?? 0}</div>
                <div className="text-[10px] text-slate-500">BE</div>
              </div>
              <div>
                <div className="text-rose-400 font-bold">{t?.losses ?? 0}</div>
                <div className="text-[10px] text-slate-500">Losses</div>
              </div>
            </div>
          </div>
        </div>

        {/* Chart 4: R Distribution Histogram */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-amber-400" />
            <h3 className="font-semibold text-white text-sm">4. R-Multiple Distribution</h3>
          </div>

          <div className="space-y-2 text-xs font-mono">
            {rBuckets.map((b) => {
              const widthPct = (b.count / maxRBucketCount) * 100;
              return (
                <div key={b.label}>
                  <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                    <span>{b.label}</span>
                    <span className="font-bold text-slate-200">{b.count} trades</span>
                  </div>
                  <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                    <div
                      style={{ width: `${b.count > 0 ? Math.max(widthPct, 8) : 0}%` }}
                      className={`h-full rounded-full ${b.color}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chart 5: Trades by Symbol */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-sky-400" />
            <h3 className="font-semibold text-white text-sm">5. Trades by Symbol</h3>
          </div>

          <div className="space-y-2.5 max-h-52 overflow-y-auto pr-1">
            {(report?.trades_by_symbol || []).length === 0 ? (
              <div className="text-slate-500 text-xs text-center py-6">No symbol metrics yet</div>
            ) : (
              (report?.trades_by_symbol || []).map((sym) => (
                <div key={sym.symbol} className="p-2.5 bg-[#0b0f19] border border-[#1e293b] rounded-lg text-xs font-mono flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-100">{sym.symbol}</span>
                    <span className="text-[10px] text-slate-500 ml-2">({sym.trades_count} trades)</span>
                  </div>
                  <div className="text-right">
                    <span className={`font-bold ${sym.total_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {sym.total_r >= 0 ? '+' : ''}{sym.total_r.toFixed(2)}R
                    </span>
                    <div className="text-[10px] text-slate-400">{sym.win_rate_pct}% WR</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Grid: Chart 6 (Side Breakdown), Chart 7 (Invalid Reasons), Chart 8 (Hourly Distribution) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Chart 6: Trades by Side (BUY vs SELL) */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-indigo-400" />
            <h3 className="font-semibold text-white text-sm">6. Trades by Direction (Side)</h3>
          </div>

          <div className="space-y-3">
            {(report?.trades_by_side || []).map((sd) => {
              const isBuy = sd.side === 'BUY';
              return (
                <div key={sd.side} className="p-3 bg-[#0b0f19] border border-[#1e293b] rounded-xl space-y-2">
                  <div className="flex justify-between items-center text-xs font-mono">
                    <span className={`px-2 py-0.5 rounded font-extrabold text-[10px] ${
                      isBuy ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                    }`}>
                      {sd.side} POSITIONS
                    </span>
                    <span className="text-slate-300 font-bold">{sd.trades_count} trades</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-1 border-t border-slate-800 text-slate-400">
                    <div>Win Rate: <span className="text-white font-bold">{sd.win_rate_pct}%</span></div>
                    <div>Realized R: <span className={sd.total_r >= 0 ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>
                      {sd.total_r >= 0 ? '+' : ''}{sd.total_r.toFixed(2)}R
                    </span></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chart 7: Invalid Signal Reasons Distribution */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <AlertOctagon className="h-5 w-5 text-rose-400" />
            <h3 className="font-semibold text-white text-sm">7. Invalid Signal Reasons</h3>
          </div>

          <div className="space-y-2.5 max-h-52 overflow-y-auto pr-1">
            {invalidReasonsList.length === 0 ? (
              <div className="text-slate-500 text-xs text-center py-6">No invalid signals rejected</div>
            ) : (
              invalidReasonsList.map((r) => {
                const widthPct = (r.count / maxReasonCount) * 100;
                return (
                  <div key={r.reason} className="text-xs font-mono">
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span className="truncate pr-2">{r.reason}</span>
                      <span className="font-bold text-rose-400">{r.count}</span>
                    </div>
                    <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${Math.max(widthPct, 10)}%` }}
                        className="h-full bg-rose-500 rounded-full"
                      />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Chart 8: Hourly Signal Distribution (0-23 UTC) */}
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-sky-400" />
            <h3 className="font-semibold text-white text-sm">8. Hourly Distribution (0-23 UTC)</h3>
          </div>

          <div className="h-44 bg-[#0b0f19] border border-[#1e293b] rounded-xl p-3 flex items-end gap-1 overflow-x-auto">
            {Array.from({ length: 24 }).map((_, hr) => {
              const hourEntry = hourlyData.find((h) => h.hour === hr);
              const count = hourEntry ? hourEntry.trades_count : 0;
              const heightPct = (count / maxHourlyCount) * 100;

              return (
                <div key={hr} className="flex-1 flex flex-col items-center min-w-[10px] group relative">
                  <div
                    style={{ height: `${count > 0 ? Math.max(heightPct, 10) : 4}%` }}
                    className={`w-full rounded-t transition-all ${count > 0 ? 'bg-sky-400' : 'bg-slate-800'}`}
                  />
                  {/* Tooltip */}
                  <div className="absolute bottom-full mb-2 hidden group-hover:block bg-slate-900 border border-slate-700 text-[10px] text-slate-200 p-2 rounded shadow-lg whitespace-nowrap z-20 font-mono">
                    <div>{hr}:00 UTC</div>
                    <div>{count} Signals/Trades</div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between text-[9px] text-slate-500 font-mono">
            <span>00:00 UTC</span>
            <span>12:00 UTC</span>
            <span>23:00 UTC</span>
          </div>
        </div>
      </div>

      {/* Provider TP vs Calculated TP Comparison Card */}
      {comp && (
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-[#1e293b] pb-3">
            <h3 className="font-semibold text-white text-sm">Signal Provider TP vs Calculated R-Multiple Comparison</h3>
            <span className="text-xs text-slate-400">Independent objective evaluation</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Provider TP Box */}
            <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-sky-400 uppercase">Provider-Specified TP</span>
                <span className="text-xs font-mono text-slate-400">{comp.provider_tp_trades_count} Trades</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center font-mono">
                <div className="p-2 bg-slate-900 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Win Rate</div>
                  <div className="text-sm font-bold text-white mt-0.5">{comp.provider_tp_win_rate_pct}%</div>
                </div>
                <div className="p-2 bg-slate-900 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Total R</div>
                  <div className={`text-sm font-bold mt-0.5 ${comp.provider_tp_total_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {comp.provider_tp_total_r >= 0 ? '+' : ''}{comp.provider_tp_total_r}R
                  </div>
                </div>
                <div className="p-2 bg-slate-900 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Avg RRR</div>
                  <div className="text-sm font-bold text-indigo-400 mt-0.5">1:{comp.provider_tp_avg_rrr}</div>
                </div>
              </div>
            </div>

            {/* Calculated TP Box */}
            <div className="bg-[#0b0f19] border border-[#1e293b] rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400 uppercase">Calculated R-Multiple TP</span>
                <span className="text-xs font-mono text-slate-400">{comp.calculated_tp_trades_count} Trades</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center font-mono">
                <div className="p-2 bg-slate-900 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Win Rate</div>
                  <div className="text-sm font-bold text-white mt-0.5">{comp.calculated_tp_win_rate_pct}%</div>
                </div>
                <div className="p-2 bg-slate-900 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Total R</div>
                  <div className={`text-sm font-bold mt-0.5 ${comp.calculated_tp_total_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {comp.calculated_tp_total_r >= 0 ? '+' : ''}{comp.calculated_tp_total_r}R
                  </div>
                </div>
                <div className="p-2 bg-slate-900 rounded border border-slate-800">
                  <div className="text-[10px] text-slate-500">Avg RRR</div>
                  <div className="text-sm font-bold text-indigo-400 mt-0.5">1:{comp.calculated_tp_avg_rrr}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
