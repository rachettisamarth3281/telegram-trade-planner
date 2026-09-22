import React, { useState } from 'react';
import { X, Edit3, Save, ShieldAlert, FileText } from 'lucide-react';
import type { TradePlanItem } from '../types';

interface TradePlanModalProps {
  plan: TradePlanItem | null;
  onClose: () => void;
  onSave: (id: string, overrides: {
    entry_price?: number;
    stop_loss?: number;
    tp1?: number;
    tp2?: number;
    tp3?: number;
    notes?: string;
  }) => Promise<void>;
}

export const TradePlanModal: React.FC<TradePlanModalProps> = ({ plan, onClose, onSave }) => {
  if (!plan) return null;

  const [entry, setEntry] = useState<string>(plan.entry_price?.toString() || '');
  const [sl, setSl] = useState<string>(plan.stop_loss?.toString() || '');
  const [tp1, setTp1] = useState<string>(plan.tp1?.toString() || '');
  const [tp2, setTp2] = useState<string>(plan.tp2?.toString() || '');
  const [tp3, setTp3] = useState<string>(plan.tp3?.toString() || '');
  const [notes, setNotes] = useState<string>(plan.notes || '');
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(plan.id, {
        entry_price: entry ? parseFloat(entry) : undefined,
        stop_loss: sl ? parseFloat(sl) : undefined,
        tp1: tp1 ? parseFloat(tp1) : undefined,
        tp2: tp2 ? parseFloat(tp2) : undefined,
        tp3: tp3 ? parseFloat(tp3) : undefined,
        notes: notes || undefined
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update trade plan');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="bg-[#111726] border border-sky-500/40 rounded-2xl max-w-xl w-full flex flex-col shadow-2xl overflow-hidden font-sans">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#1e293b] flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
              <Edit3 className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base">Manual Override: {plan.symbol} {plan.side}</h3>
              <p className="text-xs text-slate-400">
                Adjust plan parameters. Provenance will update to <span className="text-purple-400 font-bold">USER_MODIFIED</span>.
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

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Entry */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Entry Price
              </label>
              <input
                type="number"
                step="any"
                value={entry}
                onChange={(e) => setEntry(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-sky-500"
                placeholder="4350.00"
              />
            </div>

            {/* Stop Loss */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Stop Loss
              </label>
              <input
                type="number"
                step="any"
                value={sl}
                onChange={(e) => setSl(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-rose-400 font-mono focus:outline-none focus:border-rose-500"
                placeholder="4358.00"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {/* TP1 */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                TP1 (1R)
              </label>
              <input
                type="number"
                step="any"
                value={tp1}
                onChange={(e) => setTp1(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500"
                placeholder="4342.00"
              />
            </div>

            {/* TP2 */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                TP2 (2R)
              </label>
              <input
                type="number"
                step="any"
                value={tp2}
                onChange={(e) => setTp2(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500"
                placeholder="4334.00"
              />
            </div>

            {/* TP3 */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                TP3 (3R)
              </label>
              <input
                type="number"
                step="any"
                value={tp3}
                onChange={(e) => setTp3(e.target.value)}
                className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-emerald-400 font-mono focus:outline-none focus:border-emerald-500"
                placeholder="4326.00"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Personal Execution Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg px-3 py-2 text-xs text-slate-100 font-sans focus:outline-none focus:border-sky-500"
              placeholder="e.g. Adjusted SL above 1H liquidity high"
            />
          </div>

          {/* Original Record Reminder */}
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
            <FileText className="h-4 w-4 text-sky-400 shrink-0 mt-0.5" />
            <span>
              Original Telegram signal is 100% preserved in database. Modifying values will recalculate lot size and risk without overwriting raw channel history.
            </span>
          </div>

          {/* Footer Buttons */}
          <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold transition-colors cursor-pointer flex items-center gap-1.5 shadow-sm"
            >
              <Save className="h-4 w-4" />
              <span>{saving ? 'Recalculating...' : 'Save & Recalculate'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
