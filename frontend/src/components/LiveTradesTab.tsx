import React, { useState, useEffect } from 'react';
import { Sliders, Play, TrendingUp, AlertCircle, Clock } from 'lucide-react';
import type { PaperTradeItem, QuoteItem } from '../types';
import { manualCloseTrade, simulateTick } from '../lib/api';

interface LiveTradesTabProps {
  trades: PaperTradeItem[];
  quotes: Record<string, QuoteItem>;
  onTradeUpdated: () => void;
}

export const LiveTradesTab: React.FC<LiveTradesTabProps> = ({
  trades,
  quotes,
  onTradeUpdated,
}) => {
  const [isSimulating, setIsSimulating] = useState(false);
  const [tickSymbol, setTickSymbol] = useState('XAUUSD');
  const [tickPrice, setTickPrice] = useState('4358.00');
  const [tickMsg, setTickMsg] = useState<string | null>(null);
  const [closingTradeId, setClosingTradeId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(Date.now());

  // Update timer every second for duration calculations
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const openTrades = trades.filter((t) => t.status === 'OPEN');

  const handleManualClose = async (tradeId: string) => {
    setClosingTradeId(tradeId);
    try {
      await manualCloseTrade(tradeId);
      onTradeUpdated();
    } catch (e: any) {
      alert(e.message || 'Error closing trade');
    } finally {
      setClosingTradeId(null);
    }
  };

  const handleSimulateTick = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSimulating(true);
    setTickMsg(null);
    try {
      const priceNum = parseFloat(tickPrice);
      const res = await simulateTick(tickSymbol, priceNum);
      setTickMsg(`Injected ${tickSymbol} tick @ ${priceNum}. Evaluated ${res.evaluated_trades} open trades, closed ${res.closed_trades}.`);
      onTradeUpdated();
    } catch (e: any) {
      setTickMsg(`Error: ${e.message}`);
    } finally {
      setIsSimulating(false);
    }
  };

  const formatDuration = (openedAtStr: string) => {
    try {
      const opened = new Date(openedAtStr).getTime();
      const diffMs = Math.max(0, currentTime - opened);
      const diffSecs = Math.floor(diffMs / 1000);
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
      {/* Top Controls & Tick Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider">Active Monitoring</div>
              <div className="text-lg font-bold text-white">
                {openTrades.length} Simulated Position{openTrades.length === 1 ? '' : 's'}
              </div>
            </div>
          </div>
          <span className="flex h-2.5 w-2.5 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
          </span>
        </div>

        {/* Real-time Tick Injection Simulator Box */}
        <div className="lg:col-span-8 bg-[#111726] border border-[#1e293b] rounded-xl p-4">
          <form onSubmit={handleSimulateTick} className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold">
              <Sliders className="h-4 w-4 text-sky-400" />
              <span>Simulate Market Price Tick:</span>
            </div>

            <select
              value={tickSymbol}
              onChange={(e) => setTickSymbol(e.target.value)}
              className="bg-[#0b0f19] border border-[#1e293b] rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono"
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
              className="w-32 bg-[#0b0f19] border border-[#1e293b] rounded-lg px-2.5 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
            />

            <button
              type="submit"
              disabled={isSimulating}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-bold transition-all disabled:opacity-50 cursor-pointer"
            >
              <Play className="h-3.5 w-3.5" />
              {isSimulating ? 'Evaluating...' : 'Inject Tick'}
            </button>
          </form>

          {tickMsg && (
            <div className="mt-2 text-xs text-sky-400 font-mono flex items-center gap-1.5">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>{tickMsg}</span>
            </div>
          )}
        </div>
      </div>

      {/* Live / Open Trades Table */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-[#1e293b] flex items-center justify-between">
          <h3 className="font-semibold text-white text-sm">Open Positions & Real-Time Excursion Monitor</h3>
          <span className="text-xs text-slate-400">Auto-evaluates against SL/TP on every tick</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/60 border-b border-[#1e293b] text-slate-400 font-medium">
              <tr>
                <th className="p-3.5">Symbol</th>
                <th className="p-3.5">Direction</th>
                <th className="p-3.5">Entry</th>
                <th className="p-3.5">Current Price</th>
                <th className="p-3.5">SL</th>
                <th className="p-3.5">TP</th>
                <th className="p-3.5">Risk Distance</th>
                <th className="p-3.5">Target RR</th>
                <th className="p-3.5">Unrealized R</th>
                <th className="p-3.5">Duration</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b]/60">
              {openTrades.length === 0 ? (
                <tr>
                  <td colSpan={12} className="p-12 text-center text-slate-500">
                    <Clock className="h-6 w-6 mx-auto mb-2 opacity-40" />
                    No open paper trades currently running. Ingest a signal to begin monitoring.
                  </td>
                </tr>
              ) : (
                openTrades.map((t) => {
                  const quote = quotes[t.symbol];
                  const currentPrice = quote ? (t.side === 'BUY' ? quote.bid : quote.ask) : t.entry_price;
                  const riskDist = Math.abs(t.entry_price - t.effective_sl);
                  
                  // Compute dynamic unrealized R
                  let unrealizedR = 0.0;
                  if (riskDist > 0) {
                    if (t.side === 'BUY') {
                      unrealizedR = (currentPrice - t.entry_price) / riskDist;
                    } else {
                      unrealizedR = (t.entry_price - currentPrice) / riskDist;
                    }
                  }

                  const isProfitable = unrealizedR >= 0;

                  return (
                    <tr key={t.id} className="hover:bg-slate-800/40 transition-colors">
                      {/* Symbol */}
                      <td className="p-3.5 font-bold text-slate-100 font-mono text-sm">
                        {t.symbol}
                      </td>

                      {/* Direction */}
                      <td className="p-3.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold ${
                          t.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                        }`}>
                          {t.side}
                        </span>
                      </td>

                      {/* Entry */}
                      <td className="p-3.5 font-mono text-slate-300">
                        {t.entry_price.toFixed(t.symbol.includes('JPY') ? 3 : t.symbol === 'XAUUSD' ? 2 : 5)}
                      </td>

                      {/* Current Price */}
                      <td className="p-3.5 font-mono font-bold text-slate-100">
                        {currentPrice.toFixed(t.symbol.includes('JPY') ? 3 : t.symbol === 'XAUUSD' ? 2 : 5)}
                      </td>

                      {/* SL */}
                      <td className="p-3.5 font-mono text-rose-400 font-medium">
                        {t.effective_sl.toFixed(t.symbol.includes('JPY') ? 3 : t.symbol === 'XAUUSD' ? 2 : 5)}
                      </td>

                      {/* TP */}
                      <td className="p-3.5 font-mono text-emerald-400 font-medium">
                        {t.active_tp ? t.active_tp.toFixed(t.symbol.includes('JPY') ? 3 : t.symbol === 'XAUUSD' ? 2 : 5) : 'Auto R'}
                      </td>

                      {/* Risk */}
                      <td className="p-3.5 font-mono text-slate-400">
                        {riskDist.toFixed(2)} ({t.lot_size} Lots)
                      </td>

                      {/* RR */}
                      <td className="p-3.5 font-mono text-sky-400 font-bold">
                        {t.target_r_multiple.toFixed(1)}R
                      </td>

                      {/* Unrealized R */}
                      <td className="p-3.5">
                        <span className={`font-mono font-bold ${isProfitable ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {isProfitable ? '+' : ''}{unrealizedR.toFixed(2)}R
                        </span>
                      </td>

                      {/* Duration */}
                      <td className="p-3.5 font-mono text-slate-400 text-[11px]">
                        {formatDuration(t.opened_at)}
                      </td>

                      {/* Status */}
                      <td className="p-3.5">
                        <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold animate-pulse">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                          RUNNING
                        </span>
                      </td>

                      {/* Action */}
                      <td className="p-3.5 text-right">
                        <button
                          onClick={() => handleManualClose(t.id)}
                          disabled={closingTradeId === t.id}
                          className="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/30 rounded text-[11px] font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                        >
                          {closingTradeId === t.id ? 'Closing...' : 'Close (Sim)'}
                        </button>
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
