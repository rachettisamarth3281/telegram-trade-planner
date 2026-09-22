import type {
  SignalItem,
  PaperTradeItem,
  AccountInfo,
  SystemSettings,
  CompleteAnalyticsReport,
  SymbolPerformance,
  EquityCurveData,
  QuoteItem,
  TradePlanItem,
  AccountRiskStatusV1,
  InstrumentSpec
} from '../types';

const API_BASE = '/api/v1';

export async function fetchTradePlans(params?: { status?: string; symbol?: string; is_executed?: boolean }): Promise<TradePlanItem[]> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== 'ALL') query.set('status', params.status);
  if (params?.symbol) query.set('symbol', params.symbol);
  if (params?.is_executed !== undefined) query.set('is_executed', String(params.is_executed));

  const res = await fetch(`${API_BASE}/trade-plans?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch trade plans');
  return res.json();
}

export async function fetchTradePlan(id: string): Promise<TradePlanItem> {
  const res = await fetch(`${API_BASE}/trade-plans/${id}`);
  if (!res.ok) throw new Error('Failed to fetch trade plan');
  return res.json();
}

export async function overrideTradePlan(id: string, overrides: {
  entry_price?: number;
  stop_loss?: number;
  tp1?: number;
  tp2?: number;
  tp3?: number;
  notes?: string;
}): Promise<TradePlanItem> {
  const res = await fetch(`${API_BASE}/trade-plans/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(overrides)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to update trade plan' }));
    throw new Error(err.detail || 'Failed to update trade plan');
  }
  return res.json();
}

export async function markTradePlanExecuted(id: string, notes?: string): Promise<TradePlanItem> {
  const res = await fetch(`${API_BASE}/trade-plans/${id}/mark-executed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ notes })
  });
  if (!res.ok) throw new Error('Failed to mark trade plan executed');
  return res.json();
}

export async function unmarkTradePlanExecuted(id: string): Promise<TradePlanItem> {
  const res = await fetch(`${API_BASE}/trade-plans/${id}/unmark-executed`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to unmark trade plan executed');
  return res.json();
}

export async function fetchAccountRiskStatusV1(): Promise<AccountRiskStatusV1> {
  const res = await fetch(`${API_BASE}/settings/account-v1`);
  if (!res.ok) throw new Error('Failed to fetch account risk status');
  return res.json();
}

export async function updateAccountSettingsV1(payload: Partial<AccountRiskStatusV1>): Promise<AccountRiskStatusV1> {
  const res = await fetch(`${API_BASE}/settings/account-v1`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to update account settings');
  return res.json();
}

export async function fetchInstruments(): Promise<Record<string, InstrumentSpec>> {
  const res = await fetch(`${API_BASE}/settings/instruments`);
  if (!res.ok) throw new Error('Failed to fetch instruments');
  return res.json();
}

export async function updateInstrument(symbol: string, payload: Partial<InstrumentSpec>): Promise<InstrumentSpec> {
  const res = await fetch(`${API_BASE}/settings/instruments/${symbol}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to update instrument');
  return res.json();
}

export async function fetchSignals(params?: { status?: string; symbol?: string; limit?: number }): Promise<SignalItem[]> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.symbol) query.set('symbol', params.symbol);
  if (params?.limit) query.set('limit', params.limit.toString());

  const res = await fetch(`${API_BASE}/signals?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch signals');
  return res.json();
}

export async function fetchSignalDetail(id: string): Promise<SignalItem> {
  const res = await fetch(`${API_BASE}/signals/${id}`);
  if (!res.ok) throw new Error('Failed to fetch signal details');
  return res.json();
}

export async function ingestSignal(raw_text: string, options?: { channel_title?: string; target_r?: number }): Promise<SignalItem> {
  const res = await fetch(`${API_BASE}/signals/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      raw_text,
      channel_title: options?.channel_title || 'VIP Channel',
      target_r_multiple: options?.target_r || 2.0
    })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to ingest signal' }));
    throw new Error(err.detail || 'Failed to ingest signal');
  }
  return res.json();
}

export async function parsePreview(raw_text: string) {
  const res = await fetch(`${API_BASE}/signals/parse-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ raw_text })
  });
  if (!res.ok) throw new Error('Preview failed');
  return res.json();
}

export async function fetchTrades(status?: string, symbol?: string): Promise<PaperTradeItem[]> {
  const query = new URLSearchParams();
  if (status) query.set('status', status);
  if (symbol) query.set('symbol', symbol);

  const res = await fetch(`${API_BASE}/trades?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch trades');
  return res.json();
}

export async function fetchTrade(id: string): Promise<PaperTradeItem> {
  const res = await fetch(`${API_BASE}/trades/${id}`);
  if (!res.ok) throw new Error('Failed to fetch trade detail');
  return res.json();
}

export async function manualCloseTrade(tradeId: string): Promise<PaperTradeItem> {
  const res = await fetch(`${API_BASE}/trades/${tradeId}/close`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to close trade');
  return res.json();
}

export async function simulateTick(symbol: string, bid: number, ask?: number) {
  const res = await fetch(`${API_BASE}/trades/simulate-tick`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, bid, ask })
  });
  if (!res.ok) throw new Error('Failed to simulate tick');
  return res.json();
}

export async function fetchCompleteAnalyticsReport(): Promise<CompleteAnalyticsReport> {
  const res = await fetch(`${API_BASE}/analytics/report`);
  if (!res.ok) throw new Error('Failed to fetch complete analytics report');
  return res.json();
}

export async function fetchPerformanceBySymbol(): Promise<SymbolPerformance[]> {
  const res = await fetch(`${API_BASE}/analytics/by-symbol`);
  if (!res.ok) throw new Error('Failed to fetch symbol performance');
  return res.json();
}

export async function fetchEquityCurve(): Promise<EquityCurveData> {
  const res = await fetch(`${API_BASE}/analytics/equity-curve`);
  if (!res.ok) throw new Error('Failed to fetch equity curve');
  return res.json();
}

export async function fetchQuotes(): Promise<Record<string, QuoteItem>> {
  const res = await fetch(`${API_BASE}/market/quotes`);
  if (!res.ok) throw new Error('Failed to fetch market quotes');
  return res.json();
}

export async function fetchAccount(): Promise<AccountInfo> {
  const res = await fetch(`${API_BASE}/settings/account`);
  if (!res.ok) throw new Error('Failed to fetch account info');
  return res.json();
}

export async function updateAccount(payload: Partial<AccountInfo>): Promise<AccountInfo> {
  const res = await fetch(`${API_BASE}/settings/account`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to update account');
  return res.json();
}

export async function fetchSystemSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/settings/system`);
  if (!res.ok) throw new Error('Failed to fetch system settings');
  return res.json();
}

export async function updateSystemSettings(payload: Partial<SystemSettings>): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/settings/system`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to update system settings');
  return res.json();
}
