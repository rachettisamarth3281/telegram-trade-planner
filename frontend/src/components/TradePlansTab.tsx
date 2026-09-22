import React, { useState } from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';
import type { TradePlanItem } from '../types';
import { TradePlanCard } from './TradePlanCard';
import { TradePlanModal } from './TradePlanModal';

interface TradePlansTabProps {
  plans: TradePlanItem[];
  loading?: boolean;
  onRefresh?: () => void;
  onOverridePlan: (id: string, overrides: any) => Promise<void>;
  onToggleExecuted: (plan: TradePlanItem) => Promise<void>;
}

export const TradePlansTab: React.FC<TradePlansTabProps> = ({
  plans,
  loading,
  onRefresh,
  onOverridePlan,
  onToggleExecuted,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [editingPlan, setEditingPlan] = useState<TradePlanItem | null>(null);

  const filtered = plans.filter((p) => {
    if (filterStatus !== 'ALL') {
      if (filterStatus === 'READY' && p.plan_status !== 'READY') return false;
      if (filterStatus === 'WAITING_FOR_SL' && p.plan_status !== 'WAITING_FOR_SL') return false;
      if (filterStatus === 'NOT_READY' && p.plan_status !== 'NOT_READY') return false;
      if (filterStatus === 'INCOMPLETE' && p.plan_status !== 'INCOMPLETE') return false;
      if (filterStatus === 'EXECUTED' && !p.is_manually_executed) return false;
    }
    if (searchTerm.trim()) {
      const matchText = p.raw_message?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchSym = p.symbol?.toLowerCase().includes(searchTerm.toLowerCase());
      if (!matchText && !matchSym) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Search & Filter Bar */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-4 flex flex-col sm:flex-row gap-3 items-center justify-between shadow-sm">
        <div className="flex items-center gap-2 w-full sm:w-80 relative">
          <Search className="h-4 w-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search plans by text or symbol..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sky-500 font-sans"
          />
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-400" />
            <div className="flex flex-wrap gap-1 bg-[#0b0f19] p-1 border border-[#1e293b] rounded-lg">
              {[
                { id: 'ALL', label: 'ALL' },
                { id: 'READY', label: 'READY' },
                { id: 'WAITING_FOR_SL', label: 'WAITING SL' },
                { id: 'NOT_READY', label: 'NOT READY' },
                { id: 'EXECUTED', label: 'EXECUTED' },
              ].map((st) => (
                <button
                  key={st.id}
                  onClick={() => setFilterStatus(st.id)}
                  className={`px-3 py-1 rounded text-xs font-semibold font-sans transition-colors cursor-pointer ${
                    filterStatus === st.id
                      ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {st.label}
                </button>
              ))}
            </div>
          </div>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 rounded-lg bg-[#0b0f19] border border-[#1e293b] text-slate-400 hover:text-white transition-colors cursor-pointer"
              title="Refresh Plans"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Grid of Trade Plans */}
      {filtered.length === 0 ? (
        <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-12 text-center text-slate-500 text-xs">
          No trade plans match your filter criteria. Incoming Telegram signals will automatically appear here.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((plan) => (
            <TradePlanCard
              key={plan.id}
              plan={plan}
              onEdit={(p) => setEditingPlan(p)}
              onToggleExecuted={onToggleExecuted}
            />
          ))}
        </div>
      )}

      {/* Edit / Manual Override Modal */}
      {editingPlan && (
        <TradePlanModal
          plan={editingPlan}
          onClose={() => setEditingPlan(null)}
          onSave={onOverridePlan}
        />
      )}
    </div>
  );
};
