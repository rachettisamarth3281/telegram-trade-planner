import React, { useState } from 'react';
import { BookOpen, Search, Filter, ArrowUpRight, ArrowDownRight, CheckCircle2, XCircle } from 'lucide-react';
import type { PaperTradeItem } from '../types';

interface TradeJournalTabProps {
  trades: PaperTradeItem[];
}

export const TradeJournalTab: React.FC<TradeJournalTabProps> = ({ trades }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterReason, setFilterReason] = useState('ALL');

  const closedTrades = trades.filter((t) => t.status.startsWith('CLOSED'));

  const filtered = closedTrades.filter((t) => {
    if (filterReason !== 'ALL') {
      if (filterReason === 'TP_HIT' && t.exit_reason !== 'TP_HIT') return false;
      if (filterReason === 'SL_HIT' && t.exit_reason !== 'SL_HIT') return false;
      if (filterReason === 'MANUAL' && t.exit_reason !== 'MANUAL_CLOSE') return false;
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      const matchSym = t.symbol.toLowerCase().includes(term);
      const matchSide = t.side.toLowerCase().includes(term);
      const matchReason = (t.exit_reason || '').toLowerCase().includes(term);
      if (!matchSym && !matchSide && !matchReason) return false;
    }
    return true;
  });

  const formatDuration = (openedStr: string, closedStr?: string) => {
    if (!closedStr) return '--';
    try {
      const opened = new Date(openedStr).getTime();
      const closed = new Date(closedStr).getTime();
      const diffSecs = Math.max(0, Math.floor((closed - opened) / 1000));
      const hours = Math.floor(diffSecs / 3600);
      const mins = Math.floor((diffSecs % 3600) / 60);
      const secs = diffSecs % 60;

      if (hours > 0) return `${hours}h ${mins}m`;
      if (mins > 0) return `${mins}m ${secs}s`;
      return `${secs}s`;
    } catch {
      return '--';
    }
  };

  return (
    <div className="space-y-6">
      {/* Search & Reason Filter Bar */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex flex-col sm:flex-row gap-3 items-center justify-between shadow-sm">
        <div className="flex items-center gap-2 w-full sm:w-80 relative">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search journal by symbol or exit reason..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <Filter className="h-4 w-4 text-slate-400" />
          <div className="flex gap-1 bg-[#0b0f19] p-1 border border-[#1e293b] rounded-lg">
            {['ALL', 'TP_HIT', 'SL_HIT', 'MANUAL'].map((r) => (
              <button
                key={r}
                onClick={() => setFilterReason(r)}
                className={`px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
                  filterReason === r
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {r === 'TP_HIT' ? 'TP Hits' : r === 'SL_HIT' ? 'SL Hits' : r === 'MANUAL' ? 'Manual' : 'All Closed'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Trade Journal Table */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-[#1e293b] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-sky-400" />
            <h3 className="font-semibold text-white text-sm">Simulated Paper Trade Journal</h3>
          </div>
          <span className="text-xs text-slate-400">{filtered.length} closed records</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 border-b border-[#1e293b] text-slate-400 font-medium">
              <tr>
                <th className="p-3.5">Date</th>
                <th className="p-3.5">Symbol</th>
                <th className="p-3.5">Side</th>
                <th className="p-3.5">Entry</th>
                <th className="p-3.5">SL</th>
                <th className="p-3.5">TP</th>
                <th className="p-3.5">Exit</th>
                <th className="p-3.5">Exit Reason</th>
                <th className="p-3.5">P&L ($)</th>
                <th className="p-3.5">R Result</th>
                <th className="p-3.5 text-right">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b]/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={11} className="p-10 text-center text-slate-500">
                    No trade journal records found matching the filter.
                  </td>
                </tr>
              ) : (
                filtered.map((t) => {
                  const isWin = t.realized_pnl_usd > 0;
                  const isLoss = t.realized_pnl_usd < 0;
                  const dateStr = t.closed_at ? new Date(t.closed_at).toISOString().slice(0, 10) : new Date(t.opened_at).toISOString().slice(0, 10);
                  const timeStr = t.closed_at ? new Date(t.closed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

                  return (
                    <tr key={t.id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Date */}
                      <td className="p-3.5 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                        <div>{dateStr}</div>
                        <div className="text-[10px] text-slate-500">{timeStr}</div>
                      </td>

                      {/* Symbol */}
                      <td className="p-3.5 font-bold text-slate-100 font-mono">
                        {t.symbol}
                      </td>

                      {/* Side */}
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                          t.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {t.side}
                        </span>
                      </td>

                      {/* Entry */}
                      <td className="p-3.5 font-mono text-slate-300">
                        {t.entry_price}
                      </td>

                      {/* SL */}
                      <td className="p-3.5 font-mono text-rose-400">
                        {t.effective_sl}
                      </td>

                      {/* TP */}
                      <td className="p-3.5 font-mono text-emerald-400">
                        {t.active_tp ?? `${t.target_r_multiple}R Target`}
                      </td>

                      {/* Exit */}
                      <td className="p-3.5 font-mono text-slate-200">
                        {t.exit_price ?? '--'}
                      </td>

                      {/* Exit Reason */}
                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          t.exit_reason === 'TP_HIT'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25'
                            : t.exit_reason === 'SL_HIT'
                            ? 'bg-rose-500/15 text-rose-400 border border-rose-500/25'
                            : 'bg-sky-500/15 text-sky-400 border border-sky-500/25'
                        }`}>
                          {t.exit_reason === 'TP_HIT' && <CheckCircle2 className="h-3 w-3" />}
                          {t.exit_reason === 'SL_HIT' && <XCircle className="h-3 w-3" />}
                          {t.exit_reason || t.status}
                        </span>
                      </td>

                      {/* P&L ($) */}
                      <td className="p-3.5 font-mono font-bold">
                        <div className={`flex items-center gap-1 ${isWin ? 'text-emerald-400' : isLoss ? 'text-rose-400' : 'text-slate-300'}`}>
                          {isWin ? <ArrowUpRight className="h-3 w-3" /> : isLoss ? <ArrowDownRight className="h-3 w-3" /> : null}
                          <span>{isWin ? '+' : ''}${t.realized_pnl_usd.toFixed(2)}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 font-normal">
                          {t.realized_pnl_pips >= 0 ? `+${t.realized_pnl_pips}` : t.realized_pnl_pips} pips
                        </div>
                      </td>

                      {/* R Result */}
                      <td className="p-3.5 font-mono font-bold">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          isWin ? 'bg-emerald-500/10 text-emerald-400' : isLoss ? 'bg-rose-500/10 text-rose-400' : 'text-slate-400'
                        }`}>
                          {t.realized_r_multiple >= 0 ? `+${t.realized_r_multiple.toFixed(2)}R` : `${t.realized_r_multiple.toFixed(2)}R`}
                        </span>
                      </td>

                      {/* Duration */}
                      <td className="p-3.5 font-mono text-slate-400 text-right text-[11px]">
                        {formatDuration(t.opened_at, t.closed_at)}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

