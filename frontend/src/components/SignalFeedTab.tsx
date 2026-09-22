import React, { useState } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Eye,
  Radio,
  LayoutGrid,
  List
} from 'lucide-react';
import type { SignalItem } from '../types';
import { SignalDecisionCard } from './SignalDecisionCard';

interface SignalFeedTabProps {
  signals: SignalItem[];
  onSelectSignal: (sig: SignalItem) => void;
}

export const SignalFeedTab: React.FC<SignalFeedTabProps> = ({ signals, onSelectSignal }) => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('cards');

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
      {/* Search, Filter, and View Mode Bar */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex flex-col sm:flex-row gap-3 items-center justify-between shadow-sm">
        <div className="flex items-center gap-2 w-full sm:w-80 relative">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search signals by text or symbol..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 font-sans"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-400" />
            <div className="flex gap-1 bg-[#0b0f19] p-1 border border-[#1e293b] rounded-lg">
              {['ALL', 'VALID', 'INVALID', 'SKIPPED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setFilterStatus(st)}
                  className={`px-3 py-1 rounded text-xs font-semibold transition-colors cursor-pointer ${
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

          {/* View Mode Toggle */}
          <div className="flex bg-[#0b0f19] p-1 border border-[#1e293b] rounded-lg">
            <button
              onClick={() => setViewMode('cards')}
              className={`p-1.5 rounded transition-colors cursor-pointer ${
                viewMode === 'cards' ? 'bg-sky-500/20 text-sky-400' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Compact Decision Cards View"
            >
              <LayoutGrid className="h-4 w-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded transition-colors cursor-pointer ${
                viewMode === 'table' ? 'bg-sky-500/20 text-sky-400' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Full Table View"
            >
              <List className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Main Signal Display */}
      {filtered.length === 0 ? (
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-12 text-center text-slate-500 text-xs">
          No trading signals matching your search criteria.
        </div>
      ) : viewMode === 'cards' ? (
        /* Decision Cards Grid View */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((s) => (
            <SignalDecisionCard
              key={s.id}
              signal={s}
              onInspect={onSelectSignal}
            />
          ))}
        </div>
      ) : (
        /* Full Table View */
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl overflow-hidden shadow-sm">
          <div className="px-5 py-4 border-b border-[#1e293b] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Radio className="h-4 w-4 text-sky-400" />
              <h3 className="font-semibold text-white text-sm">Telegram Signal Ingestion Feed</h3>
            </div>
            <span className="text-xs text-slate-400">{filtered.length} total recorded</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/60 border-b border-[#1e293b] text-slate-400 font-medium">
                <tr>
                  <th className="p-3.5">Timestamp</th>
                  <th className="p-3.5">Original Signal</th>
                  <th className="p-3.5">Parsed Direction</th>
                  <th className="p-3.5">Entry</th>
                  <th className="p-3.5">SL</th>
                  <th className="p-3.5">Provider TP</th>
                  <th className="p-3.5">Calculated TP</th>
                  <th className="p-3.5">Parser Status</th>
                  <th className="p-3.5">Validation Status</th>
                  <th className="p-3.5 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e293b]/60">
                {filtered.map((s) => {
                  const isValid = s.validation_status === 'VALID';
                  const isSkipped = s.validation_status.startsWith('SKIPPED');
                  const providerTpsStr = s.provider_tps && s.provider_tps.length > 0 ? s.provider_tps.join(', ') : 'None';

                  return (
                    <tr
                      key={s.id}
                      onClick={() => onSelectSignal(s)}
                      className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    >
                      <td className="p-3.5 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                        {new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        <div className="text-[10px] text-slate-500">{new Date(s.created_at).toISOString().slice(0, 10)}</div>
                      </td>

                      <td className="p-3.5 max-w-xs">
                        <pre className="font-mono text-slate-300 text-[11px] whitespace-pre-wrap line-clamp-2 bg-slate-900/70 p-1.5 rounded border border-slate-800">
                          {s.raw_text}
                        </pre>
                      </td>

                      <td className="p-3.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-100">{s.symbol || 'N/A'}</span>
                          {s.side && (
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-extrabold ${
                              s.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                            }`}>
                              {s.side}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="p-3.5 font-mono text-slate-200">
                        {s.entry_price ?? '--'}
                      </td>

                      <td className="p-3.5 font-mono text-rose-400">
                        {s.provider_sl ?? 'None'}
                      </td>

                      <td className="p-3.5 font-mono text-emerald-400">
                        {providerTpsStr}
                      </td>

                      <td className="p-3.5 font-mono text-sky-400">
                        {s.metrics?.r2_target ? `${s.metrics.r2_target} (2R)` : 'Auto (2R)'}
                      </td>

                      <td className="p-3.5">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          {((s.parser_confidence || 1.0) * 100).toFixed(0)}% Conf
                        </span>
                      </td>

                      <td className="p-3.5">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${
                          isValid
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : isSkipped
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        }`}>
                          {isValid && <CheckCircle2 className="h-3 w-3" />}
                          {!isValid && !isSkipped && <XCircle className="h-3 w-3" />}
                          {isSkipped && <AlertTriangle className="h-3 w-3" />}
                          {s.validation_status}
                        </span>
                      </td>

                      <td className="p-3.5 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectSignal(s);
                          }}
                          className="p-1.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors cursor-pointer"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
