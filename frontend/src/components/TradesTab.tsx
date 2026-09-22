import React, { useState } from 'react';
import { Sliders, Play } from 'lucide-react';
import type { PaperTradeItem } from '../types';
import { manualCloseTrade, simulateTick } from '../lib/api';

interface TradesTabProps {
  trades: PaperTradeItem[];
  onTradeUpdated: () => void;
}

export const TradesTab: React.FC<TradesTabProps> = ({ trades, onTradeUpdated }) => {
  const [activeSubTab, setActiveSubTab] = useState<'OPEN' | 'CLOSED' | 'ALL'>('OPEN');
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickSymbol, setTickSymbol] = useState('XAUUSD');
  const [tickPrice, setTickPrice] = useState('4358.00');
  const [tickMsg, setTickMsg] = useState<string | null>(null);

  const handleManualClose = async (tradeId: string) => {
    try {
      await manualCloseTrade(tradeId);
      onTradeUpdated();
    } catch (e: any) {
      alert(e.message || 'Error closing trade');
    }
  };

  const handleSimulateTick = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    setTickMsg(null);
    try {
      const priceNum = parseFloat(tickPrice);
      const res = await simulateTick(tickSymbol, priceNum);
      setTickMsg(`Injected tick ${tickSymbol} @ ${priceNum}. Evaluated ${res.evaluated_trades} trades, closed ${res.closed_trades}.`);
      onTradeUpdated();
    } catch (e: any) {
      setTickMsg(`Error: ${e.message}`);
    } finally {
      setIsSimulating(false);
    }
  };

  const filtered = trades.filter((t) => {
    if (activeSubTab === 'OPEN') return t.status === 'OPEN';
    if (activeSubTab === 'CLOSED') return t.status.startsWith('CLOSED');
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Action & Simulation Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sub-tab navigation */}
        <div className="lg:col-span-6 bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex items-center justify-between">
          <div className="flex gap-2">
            {(['OPEN', 'CLOSED', 'ALL'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveSubTab(tab)}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                  activeSubTab === tab
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {tab === 'OPEN' && `Active (${trades.filter(t => t.status === 'OPEN').length})`}
                {tab === 'CLOSED' && `Closed (${trades.filter(t => t.status.startsWith('CLOSED')).length})`}
                {tab === 'ALL' && `All (${trades.length})`}
              </button>
            ))}
          </div>
        </div>

        {/* Real-time Tick Simulator Box */}
        <div className="lg:col-span-6 bg-[#111726] border border-[#1e293b] rounded-xl p-4">
          <form onSubmit={handleSimulateTick} className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold">
              <Sliders className="h-4 w-4 text-sky-400" />
              <span>Simulate Market Tick:</span>
            </div>

            <select
              value={tickSymbol}
              onChange={(e) => setTickSymbol(e.target.value)}
              className="bg-[#0b0f19] border border-[#1e293b] rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="XAUUSD">XAUUSD (Gold)</option>
              <option value="EURUSD">EURUSD</option>
              <option value="GBPUSD">GBPUSD</option>
              <option value="USDJPY">USDJPY</option>
              <option value="US30">US30</option>
              <option value="BTCUSD">BTCUSD</option>
            </select>

            <input
              type="number"
              step="any"
              placeholder="Tick Price"
              value={tickPrice}
              onChange={(e) => setTickPrice(e.target.value)}
              className="w-28 bg-[#0b0f19] border border-[#1e293b] rounded-lg px-2.5 py-1 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
            />

            <button
              type="submit"
              disabled={isSimulating}
              className="flex items-center gap-1.5 px-3 py-1 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
            >
              <Play className="h-3 w-3" />
              {isSimulating ? 'Testing...' : 'Inject Tick'}
            </button>
          </form>

          {tickMsg && (
            <div className="mt-2 text-[11px] text-sky-400 font-mono">
              {tickMsg}
            </div>
          )}
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/60 border-b border-[#1e293b] text-slate-400 font-medium">
            <tr>
              <th className="p-3.5">Asset & Side</th>
              <th className="p-3.5">Size / Entry</th>
              <th className="p-3.5">Effective SL</th>
              <th className="p-3.5">Target TP</th>
              <th className="p-3.5">Excursion (MFE / MAE)</th>
              <th className="p-3.5">Realized P&L</th>
              <th className="p-3.5">Status / Reason</th>
              <th className="p-3.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1e293b]/60">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-500">
                  No paper trades found in this category.
                </td>
              </tr>
            ) : (
              filtered.map((t) => {
                const isOpen = t.status === 'OPEN';
                const isWin = t.realized_pnl_usd > 0;
                const isLoss = t.realized_pnl_usd < 0;

                return (
                  <tr key={t.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-3.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-100 text-sm">{t.symbol}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-extrabold ${
                          t.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {t.side}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                        ID: {t.id.slice(0, 8)}
                      </div>
                    </td>

                    <td className="p-3.5">
                      <div className="font-mono text-slate-200">{t.lot_size} Lots</div>
                      <div className="text-[11px] font-mono text-slate-400">@ {t.entry_price}</div>
                    </td>

                    <td className="p-3.5 font-mono text-rose-400">
                      {t.effective_sl}
                    </td>

                    <td className="p-3.5 font-mono text-emerald-400">
                      {t.active_tp ?? `${t.target_r_multiple}R Target`}
                    </td>

                    <td className="p-3.5">
                      <div className="font-mono text-[11px] space-y-0.5">
                        <div className="text-emerald-400">MFE: +{t.max_favorable_r}R</div>
                        <div className="text-rose-400">MAE: {t.max_adverse_r}R</div>
                      </div>
                    </td>

                    <td className="p-3.5">
                      {isOpen ? (
                        <span className="text-slate-400 font-mono italic">Running...</span>
                      ) : (
                        <div>
                          <div className={`font-bold font-mono ${isWin ? 'text-emerald-400' : isLoss ? 'text-rose-400' : 'text-slate-300'}`}>
                            {isWin ? '+' : ''}${t.realized_pnl_usd.toFixed(2)}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400">
                            {t.realized_r_multiple > 0 ? `+${t.realized_r_multiple}R` : `${t.realized_r_multiple}R`} ({t.realized_pnl_pips} pips)
                          </div>
                        </div>
                      )}
                    </td>

                    <td className="p-3.5">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                        isOpen
                          ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                          : isWin
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {isOpen ? 'RUNNING' : t.exit_reason || t.status}
                      </span>
                      {t.closed_at && (
                        <div className="text-[10px] text-slate-500 mt-1">
                          Closed: {new Date(t.closed_at).toLocaleTimeString()}
                        </div>
                      )}
                    </td>

                    <td className="p-3.5 text-right">
                      {isOpen && (
                        <button
                          onClick={() => handleManualClose(t.id)}
                          className="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 rounded text-[11px] font-semibold transition-colors"
                        >
                          Manual Close
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

