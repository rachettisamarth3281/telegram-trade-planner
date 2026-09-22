import { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { PaperTradingBanner } from './components/PaperTradingBanner';
import { AccountRiskBar } from './components/AccountRiskBar';
import { TradePlansTab } from './components/TradePlansTab';
import { OverviewTab } from './components/OverviewTab';
import { LiveTradesTab } from './components/LiveTradesTab';
import { SignalFeedTab } from './components/SignalFeedTab';
import { TradeJournalTab } from './components/TradeJournalTab';
import { AnalyticsTab } from './components/AnalyticsTab';
import { SandboxTab } from './components/SandboxTab';
import { SettingsTab } from './components/SettingsTab';
import { SignalDetailModal } from './components/SignalDetailModal';
import { useWebSocket, type WSEvent } from './hooks/useWebSocket';
import type {
  SignalItem,
  PaperTradeItem,
  AccountInfo,
  CompleteAnalyticsReport,
  QuoteItem,
  TradePlanItem,
  AccountRiskStatusV1
} from './types';
import {
  fetchSignals,
  fetchTrades,
  fetchAccount,
  fetchCompleteAnalyticsReport,
  fetchQuotes,
  fetchTradePlans,
  fetchAccountRiskStatusV1,
  overrideTradePlan,
  markTradePlanExecuted,
  unmarkTradePlanExecuted
} from './lib/api';

export function App() {
  const [activeTab, setActiveTab] = useState('trade-plans');
  const [tradePlans, setTradePlans] = useState<TradePlanItem[]>([]);
  const [signals, setSignals] = useState<SignalItem[]>([]);
  const [trades, setTrades] = useState<PaperTradeItem[]>([]);
  const [account, setAccount] = useState<AccountInfo | undefined>();
  const [accountRisk, setAccountRisk] = useState<AccountRiskStatusV1 | null>(null);
  const [analytics, setAnalytics] = useState<CompleteAnalyticsReport | undefined>();
  const [quotes, setQuotes] = useState<Record<string, QuoteItem>>({});
  const [loading, setLoading] = useState(true);
  const [selectedSignal, setSelectedSignal] = useState<SignalItem | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [plans, sigs, trds, acc, accRisk, anl, qts] = await Promise.all([
        fetchTradePlans(),
        fetchSignals({ limit: 100 }),
        fetchTrades(),
        fetchAccount(),
        fetchAccountRiskStatusV1().catch(() => null),
        fetchCompleteAnalyticsReport(),
        fetchQuotes()
      ]);
      setTradePlans(plans);
      setSignals(sigs);
      setTrades(trds);
      setAccount(acc);
      setAccountRisk(accRisk);
      setAnalytics(anl);
      setQuotes(qts);
    } catch (e) {
      console.error('Error loading dashboard data', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 8000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleWsEvent = useCallback((evt: WSEvent) => {
    if (evt.event === 'NEW_SIGNAL' || evt.event === 'TRADE_OPENED' || evt.event === 'TRADE_CLOSED') {
      loadData();
    } else if (evt.event === 'PRICE_UPDATE') {
      setQuotes((prev) => ({
        ...prev,
        [evt.data.symbol]: {
          bid: evt.data.bid,
          ask: evt.data.ask,
          last_update: Date.now() / 1000
        }
      }));
    }
  }, [loadData]);

  const { isConnected: isWsConnected } = useWebSocket(handleWsEvent);
  const openTrades = trades.filter((t) => t.status === 'OPEN');
  const readyPlans = tradePlans.filter((p) => p.plan_status === 'READY');

  const handleOverridePlan = async (id: string, overrides: any) => {
    await overrideTradePlan(id, overrides);
    await loadData();
  };

  const handleToggleExecuted = async (plan: TradePlanItem) => {
    if (plan.is_manually_executed) {
      await unmarkTradePlanExecuted(plan.id);
    } else {
      await markTradePlanExecuted(plan.id);
    }
    await loadData();
  };

  const linkedTrade = selectedSignal?.paper_trade_id
    ? trades.find((t) => t.id === selectedSignal.paper_trade_id)
    : null;

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* 1. Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        accountRisk={accountRisk || undefined}
        isWsConnected={isWsConnected}
        readyPlansCount={readyPlans.length}
      />

      {/* 2. Paper Trading Notice Banner */}
      <PaperTradingBanner />

      {/* 3. Main Dashboard Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Account Risk & Budget Status Bar */}
        <AccountRiskBar
          status={accountRisk}
          loading={loading}
          onRefresh={loadData}
        />

        {loading ? (
          <div className="h-72 flex flex-col items-center justify-center text-slate-400 text-sm">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-500 mb-3" />
            <span>Loading trade planner and signal engine state...</span>
          </div>
        ) : (
          <>
            {/* Primary V1 Tab: Trade Plans */}
            {activeTab === 'trade-plans' && (
              <TradePlansTab
                plans={tradePlans}
                loading={loading}
                onRefresh={loadData}
                onOverridePlan={handleOverridePlan}
                onToggleExecuted={handleToggleExecuted}
              />
            )}

            {activeTab === 'signals' && (
              <SignalFeedTab
                signals={signals}
                onSelectSignal={setSelectedSignal}
              />
            )}

            {activeTab === 'live-trades' && (
              <LiveTradesTab
                trades={trades}
                quotes={quotes}
                onTradeUpdated={loadData}
              />
            )}

            {activeTab === 'journal' && (
              <TradeJournalTab
                trades={trades}
              />
            )}

            {activeTab === 'analytics' && (
              <AnalyticsTab />
            )}

            {activeTab === 'sandbox' && (
              <SandboxTab />
            )}

            {activeTab === 'settings' && (
              <SettingsTab
                account={account}
                onAccountUpdated={loadData}
              />
            )}

            {activeTab === 'overview' && (
              <OverviewTab
                analytics={analytics}
                recentSignals={signals}
                openTrades={openTrades}
                onSignalIngested={loadData}
                onNavigateTab={setActiveTab}
                onSelectSignal={setSelectedSignal}
              />
            )}
          </>
        )}
      </main>

      {/* Signal Detail Modal */}
      <SignalDetailModal
        signal={selectedSignal}
        trade={linkedTrade}
        onClose={() => setSelectedSignal(null)}
      />
    </div>
  );
}

export default App;
