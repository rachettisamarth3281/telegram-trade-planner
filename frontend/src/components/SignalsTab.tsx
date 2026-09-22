import React, { useState } from 'react';
import { Search, Filter, CheckCircle2, XCircle, AlertTriangle, Layers, Eye } from 'lucide-react';
import type { SignalItem } from '../types';

interface SignalsTabProps {
  signals: SignalItem[];
}

export const SignalsTab: React.FC<SignalsTabProps> = ({ signals }) => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [selectedSignal, setSelectedSignal] = useState<SignalItem | null>(null);

  const filtered = signals.filter((sig) => {
    if (filterStatus !== 'ALL') {
      if (filterStatus === 'VALID' && sig.validation_status !== 'VALID') return false;
      if (filterStatus === 'INVALID' && sig.validation_status !== 'INVALID') return false;
      if (filterStatus === 'SKIPPED' && !sig.validation_status.startsWith('SKIPPED')) return false;
    }
    if (searchTerm.trim()) {
      const matchText = sig.raw_text.toLowerCase().includes(searchTerm.toLowerCase());
      const matchSym = sig.symbol?.toLowerCase().includes(searchTerm.toLowerCase());
      if (!matchText && !matchSym) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Filter and Search Bar */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex flex-col sm:flex-row gap-3 items-center justify-between">
        <div className="flex items-center gap-2 w-full sm:w-80 relative">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search signals by text or symbol..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
          <Filter className="h-4 w-4 text-slate-400" />
          <div className="flex gap-1 bg-[#0b0f19] p-1 border border-[#1e293b] rounded-lg">
            {['ALL', 'VALID', 'INVALID', 'SKIPPED'].map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-3 py-1 rounded text-xs font-semibold transition-colors ${
                  filterStatus === st
                    ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Signal List & Audit Inspector Modal/Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Signal List Table */}
        <div className={`space-y-3 ${selectedSignal ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          <div className="bg-[#111726] border border-[#1e293b] rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/60 border-b border-[#1e293b] text-slate-400 font-medium">
                <tr>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Asset & Side</th>
                  <th className="p-3.5">Entry / SL / TP</th>
                  <th className="p-3.5">Calculated Targets</th>
                  <th className="p-3.5">Timestamp</th>
                  <th className="p-3.5 text-right">Audit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]/60">
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-8 text-center text-slate-500">
                      No signals matching your search criteria.
                    </td>
                  </tr>
                ) : (
                  filtered.map((s) => (
                    <tr
                      key={s.id}
                      onClick={() => setSelectedSignal(s)}
                      className={`cursor-pointer hover:bg-slate-800/40 transition-colors ${
                        selectedSignal?.id === s.id ? 'bg-sky-500/10' : ''
                      }`}
                    >
                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          s.validation_status === 'VALID'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : s.validation_status.startsWith('SKIPPED')
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}>
                          {s.validation_status === 'VALID' && <CheckCircle2 className="h-3 w-3" />}
                          {s.validation_status === 'INVALID' && <XCircle className="h-3 w-3" />}
                          {s.validation_status.startsWith('SKIPPED') && <AlertTriangle className="h-3 w-3" />}
                          {s.validation_status}
                        </span>
                      </td>

                      <td className="p-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-100">{s.symbol || 'N/A'}</span>
                          {s.side && (
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-extrabold ${
                              s.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                            }`}>
                              {s.side}
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                          Confidence: {(s.parser_confidence * 100).toFixed(0)}%
                        </div>
                      </td>

                      <td className="p-3.5">
                        <div className="font-mono text-slate-200">Entry: {s.entry_price ?? 'N/A'}</div>
                        <div className="text-[10px] font-mono text-rose-400">SL: {s.provider_sl ?? 'None'}</div>
                        <div className="text-[10px] font-mono text-emerald-400">
                          TPs: {s.provider_tps?.length ? s.provider_tps.join(', ') : 'Auto R'}
                        </div>
                      </td>

                      <td className="p-3.5">
                        {s.metrics ? (
                          <div className="space-y-0.5 text-[11px] font-mono">
                            <div className="text-slate-300">1R: {s.metrics.r1_target}</div>
                            <div className="text-slate-300">2R: {s.metrics.r2_target}</div>
                            <div className="text-xs text-sky-400">Risk: {s.metrics.risk_pips} pips</div>
                          </div>
                        ) : (
                          <span className="text-slate-500 text-[11px]">No calculations</span>
                        )}
                      </td>

                      <td className="p-3.5 text-slate-400 text-[11px]">
                        {new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>

                      <td className="p-3.5 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedSignal(s);
                          }}
                          className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-white"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Audit Inspector Panel */}
        {selectedSignal && (
          <div className="lg:col-span-5 bg-[#111726] border border-sky-500/40 rounded-xl p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-[#1e293b] pb-3">
              <div className="flex items-center gap-2">
                <Layers className="h-5 w-5 text-sky-400" />
                <h3 className="font-semibold text-white">Full Signal Audit Trail</h3>
              </div>
              <button
                onClick={() => setSelectedSignal(null)}
                className="text-xs text-slate-400 hover:text-white px-2 py-1 bg-slate-800 rounded"
              >
                Close ✕
              </button>
            </div>

            {/* Raw Message Card */}
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Original Telegram Message
              </span>
              <pre className="bg-[#0b0f19] border border-[#1e293b] rounded-lg p-3 text-xs text-slate-200 font-mono whitespace-pre-wrap">
                {selectedSignal.raw_text}
              </pre>
            </div>

            {/* Validation & Status */}
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Validation & Rejection Audit
              </span>
              <div className={`p-3 rounded-lg text-xs ${
                selectedSignal.validation_status === 'VALID'
                  ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
              }`}>
                <div className="font-bold">Status: {selectedSignal.validation_status}</div>
                {selectedSignal.rejection_reason && (
                  <div className="mt-1 text-rose-300">Reason: {selectedSignal.rejection_reason}</div>
                )}
              </div>
            </div>

            {/* Mathematical Calculations Breakdown */}
            {selectedSignal.metrics && (
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
                  Calculated Risk & R-Multiples
                </span>
                <div className="bg-[#0b0f19] border border-[#1e293b] rounded-lg p-3 space-y-2 text-xs font-mono">
                  <div className="flex justify-between border-b border-slate-800 pb-1">
                    <span className="text-slate-400">Effective SL:</span>
                    <span className="text-rose-400 font-bold">{selectedSignal.metrics.effective_sl} ({selectedSignal.metrics.sl_source})</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-1">
                    <span className="text-slate-400">Risk Distance:</span>
                    <span className="text-slate-200">{selectedSignal.metrics.risk_price_diff} ({selectedSignal.metrics.risk_pips} pips)</span>
                  </div>
                  <div className="flex justify-between text-emerald-400">
                    <span>1.0R Target:</span>
                    <span>{selectedSignal.metrics.r1_target}</span>
                  </div>
                  <div className="flex justify-between text-emerald-400">
                    <span>1.5R Target:</span>
                    <span>{selectedSignal.metrics.r1_5_target}</span>
                  </div>
                  <div className="flex justify-between text-emerald-400 font-bold">
                    <span>2.0R Target (Standard):</span>
                    <span>{selectedSignal.metrics.r2_target}</span>
                  </div>
                  <div className="flex justify-between text-emerald-400">
                    <span>3.0R Target:</span>
                    <span>{selectedSignal.metrics.r3_target}</span>
                  </div>
                  <div className="flex justify-between pt-1 border-t border-slate-800 text-sky-400">
                    <span>Suggested Lot Size:</span>
                    <span>{selectedSignal.metrics.suggested_lot_size} Lots (${selectedSignal.metrics.risk_amount_usd} risk)</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

