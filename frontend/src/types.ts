export type ValueProvenance = 'TELEGRAM' | 'SYSTEM_CALCULATED' | 'USER_MODIFIED';

export type TradePlanStatus =
  | 'RECEIVED'
  | 'ANALYZING'
  | 'SIGNAL_DETECTED'
  | 'WAITING_FOR_SL'
  | 'READY'
  | 'INCOMPLETE'
  | 'NOT_READY'
  | 'REJECTED'
  | 'MARKED_EXECUTED';

export interface TradePlanItem {
  id: string;
  signal_id: string;
  symbol: string;
  side: string;
  order_type: string;
  entry_price?: number;
  entry_zone_low?: number;
  entry_zone_high?: number;
  entry_provenance: ValueProvenance;
  stop_loss?: number;
  sl_provenance: ValueProvenance;
  tp1?: number;
  tp1_provenance: ValueProvenance;
  tp2?: number;
  tp2_provenance: ValueProvenance;
  tp3?: number;
  tp3_provenance: ValueProvenance;
  calculated_lot_size: number;
  monetary_risk_inr: number;
  monetary_risk_usd: number;
  risk_distance_points?: number;
  reward_risk_ratio_tp1?: number;
  reward_risk_ratio_tp2?: number;
  reward_risk_ratio_tp3?: number;
  plan_status: TradePlanStatus;
  guard_rejection_reason?: string;
  is_manually_executed: boolean;
  executed_at?: string;
  notes?: string;
  calculation_details?: Record<string, any>;
  original_telegram_values?: Record<string, any>;
  raw_message: string;
  created_at?: string;
  updated_at?: string;
}

export interface AccountRiskStatusV1 {
  account_currency: string;
  initial_balance: number;
  current_balance: number;
  daily_starting_balance: number;
  risk_percent: number;
  max_risk_per_trade_inr: number;
  max_daily_risk_pct: number;
  daily_risk_limit_inr: number;
  daily_risk_used_inr: number;
  daily_risk_remaining_inr: number;
  open_trades_count: number;
  max_open_trades: number;
  usd_inr_conversion_mode: string;
  manual_usd_inr_rate: number;
}

export interface InstrumentSpec {
  symbol: string;
  contract_size: number;
  tick_size: number;
  min_volume: number;
  volume_step: number;
  profit_currency: string;
  description: string;
}

export interface CalculatedMetrics {
  effective_sl: number;
  sl_source: string;
  risk_price_diff: number;
  risk_pips: number;
  r1_target: number;
  r1_5_target: number;
  r2_target: number;
  r3_target: number;
  r_targets: Record<string, number>;
  provider_tp_rrrs: Record<string, number>;
  suggested_lot_size?: number;
  risk_amount_usd?: number;
}

export interface SignalItem {
  id: string;
  raw_message_id: string;
  raw_text: string;
  symbol?: string;
  side?: string;
  order_type: string;
  entry_price?: number;
  entry_zone_low?: number;
  entry_zone_high?: number;
  entry_reference_price?: number;
  execution_style?: string;
  message_type?: string;
  parent_signal_id?: string;
  provider_sl?: number;
  provider_tps: number[];
  targets_json?: string;
  provider_outcomes_json?: string;
  management_events_json?: string;
  parser_confidence: number;
  validation_status: string; // VALID, INVALID, SKIPPED_NO_SL
  rejection_reason?: string;
  created_at: string;
  metrics?: CalculatedMetrics;
  paper_trade_id?: string;
}

export interface TradeEvent {
  id: string;
  event_type: string;
  price?: number;
  details?: any;
  created_at: string;
}

export interface TradeAuditProvenance {
  original_telegram_message: string;
  telegram_message_id?: number;
  source_chat_title?: string;
  extracted_values: Record<string, any>;
  sl_source: string;
  tp_source: string;
  tp_formula: string;
  initial_risk_distance: number;
  initial_risk_pips: number;
  initial_risk_amount_usd: number;
  risk_reward_ratio: string;
  validation_status: string;
  decision_reason: string;
  closing_price?: number;
  closing_reason?: string;
  final_realized_r?: number;
}

export interface PaperTradeItem {
  id: string;
  signal_id: string;
  account_id: string;
  symbol: string;
  side: string;
  status: string; // OPEN, CLOSED_TP, CLOSED_SL, CLOSED_MANUAL, CANCELLED
  lot_size: number;
  entry_price: number;
  entry_zone_low?: number;
  entry_zone_high?: number;
  effective_sl: number;
  active_tp?: number;
  target_r_multiple: number;
  provider_claimed_pips?: number;
  provider_claimed_status?: string;
  is_risk_free_moved?: boolean;
  trailing_sl?: number;
  opened_at: string;
  closed_at?: string;
  exit_price?: number;
  exit_reason?: string;
  realized_pnl_usd: number;
  realized_pnl_pips: number;
  realized_r_multiple: number;
  max_favorable_r: number;
  max_adverse_r: number;
  events?: TradeEvent[];
  provenance?: TradeAuditProvenance;
}

export interface SystemSettings {
  default_r_multiple: number;
  alternative_r_multiples: number[];
  min_risk_reward_ratio: number;
  paper_trading_mode: boolean;
  position_sizing_mode: 'FIXED_LOT' | 'FIXED_RISK_AMOUNT' | 'PERCENTAGE_RISK' | string;
  fixed_risk_amount: number;
  market_data_provider: 'MOCK' | 'MT5' | string;
  candle_execution_policy: 'CONSERVATIVE' | 'SL_FIRST' | 'TP_FIRST' | 'BAR_CLOSE' | string;
  initial_balance: number;
  current_balance: number;
  risk_percent: number;
}

export interface AccountInfo {
  id: string;
  name: string;
  currency: string;
  initial_balance: number;
  current_balance: number;
  current_equity: number;
  risk_percent: number;
  default_r_target: number;
  paper_trading_mode?: boolean;
}

export interface SignalOverview {
  total_signals: number;
  valid_signals: number;
  invalid_signals: number;
  validity_rate_pct: number;
  invalid_signal_reasons: Record<string, number>;
}

export interface TradeOverview {
  paper_trades: number;
  open_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  breakeven: number;
  win_rate_pct: number;
}

export interface PerformanceMetrics {
  total_realized_r: number;
  average_r_per_trade: number;
  average_win_r: number;
  average_loss_r: number;
  profit_factor: number;
  max_winning_streak: number;
  max_losing_streak: number;
  max_drawdown_r: number;
  max_drawdown_usd: number;
  average_risk_reward: number;
  net_pnl_usd: number;
  total_pips: number;
}

export interface ProviderTPComparison {
  provider_tp_trades_count: number;
  calculated_tp_trades_count: number;
  provider_tp_win_rate_pct: number;
  calculated_tp_win_rate_pct: number;
  provider_tp_total_r: number;
  calculated_tp_total_r: number;
  provider_tp_avg_rrr: number;
  calculated_tp_avg_rrr: number;
}

export interface SymbolPerformance {
  symbol: string;
  trades_count: number;
  closed_trades: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  total_r: number;
  net_pnl_usd: number;
}

export interface SidePerformance {
  side: string;
  trades_count: number;
  closed_trades: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  total_r: number;
  net_pnl_usd: number;
}

export interface DatePerformance {
  date: string;
  trades_count: number;
  wins: number;
  losses: number;
  total_r: number;
  net_pnl_usd: number;
}

export interface HourPerformance {
  hour: number;
  trades_count: number;
  total_r: number;
  net_pnl_usd: number;
}

export interface CompleteAnalyticsReport {
  signals: SignalOverview;
  trades: TradeOverview;
  performance: PerformanceMetrics;
  provider_comparison: ProviderTPComparison;
  trades_by_symbol: SymbolPerformance[];
  trades_by_side: SidePerformance[];
  trades_by_date: DatePerformance[];
  trades_by_hour: HourPerformance[];
}

export interface EquityCurveData {
  total_trades: number;
  cumulative_pnl: number;
  cumulative_r: number;
  curve: {
    trade_index: number;
    trade_id: string;
    symbol: string;
    closed_at?: string;
    realized_pnl: number;
    realized_r: number;
    cumulative_pnl: number;
    cumulative_r: number;
  }[];
}

export interface QuoteItem {
  bid: number;
  ask: number;
  last_update: number;
}
