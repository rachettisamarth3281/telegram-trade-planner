import React, { useState, useEffect } from 'react';
import { Terminal } from 'lucide-react';
import { parsePreview } from '../lib/api';
import { SignalDecisionCard } from './SignalDecisionCard';
import type { SignalItem } from '../types';

export const SandboxTab: React.FC = () => {
  const [inputText, setInputText] = useState('Sell gold @ 4350.53\nSL 4358');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const runPreview = async (text: string) => {
    if (!text.trim()) {
      setResult(null);
      return;
    }
    setLoading(true);
    try {
      const data = await parsePreview(text);
      setResult(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      runPreview(inputText);
    }, 200);
    return () => clearTimeout(timer);
  }, [inputText]);

  const presetExamples = [
    {
      title: "Gold Benchmark (Sell gold @ 4350.53 SL 4358)",
      text: "Sell gold @ 4350.53\nSL 4358"
    },
    {
      title: "EURUSD Multi-TP VIP",
      text: "🔥 VIP SIGNAL 🔥\nBUY EURUSD CMP 1.08500\nSL: 1.08000\nTP1: 1.09000\nTP2: 1.09500\nTP3: 1.10000"
    },
    {
      title: "US30 Short Limit",
      text: "US30 SHORT LIMIT @ 38900\nSL 39050\nTP 38500"
    },
    {
      title: "Invalid BUY (SL > Entry)",
      text: "BUY EURUSD @ 1.08500\nSL 1.09000"
    },
    {
      title: "Missing SL (Strictly Rejected)",
      text: "BUY GOLD @ 2350.00\nTP 2380.00"
    }
  ];

  // Convert sandbox preview result to SignalItem shape for SignalDecisionCard
  const previewSignalItem: SignalItem | null = result ? {
    id: 'sandbox-preview',
    raw_message_id: 'sandbox-preview',
    raw_text: inputText,
    symbol: result.symbol,
    side: result.side,
    order_type: result.order_type || 'MARKET',
    entry_price: result.entry_price,
    provider_sl: result.provider_sl,
    provider_tps: result.provider_tps || [],
    parser_confidence: result.parser_confidence || 1.0,
    validation_status: result.validation_status || (result.is_valid ? 'VALID' : 'INVALID'),
    rejection_reason: result.rejection_reasons?.length ? result.rejection_reasons.join('; ') : undefined,
    created_at: new Date().toISOString(),
    metrics: result.metrics,
  } : null;

  return (
    <div className="space-y-6">
      {/* Intro Header */}
      <div className="bg-[#111726] border border-[#1e293b] rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Terminal className="h-5 w-5 text-sky-400" />
            <h2 className="text-lg font-bold text-white">Interactive Signal Parser & Decision Card Sandbox</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Test any raw Telegram signal format in real-time. Zero database modifications occur in sandbox mode.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-mono">
            Zero-Assumption SL Engine
          </span>
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="flex flex-wrap gap-2">
        {presetExamples.map((ex) => (
          <button
            key={ex.title}
            onClick={() => setInputText(ex.text)}
            className="px-3 py-1.5 rounded-lg bg-[#111726] hover:bg-slate-800 border border-[#1e293b] text-xs text-slate-300 transition-colors cursor-pointer"
          >
            {ex.title}
          </button>
        ))}
      </div>

      {/* 2-Column Playground */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Textarea */}
        <div className="lg:col-span-6 bg-[#111726] border border-[#1e293b] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Input Raw Telegram Signal
            </label>
            {loading && <span className="text-xs text-sky-400 animate-pulse">Parsing...</span>}
          </div>

          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            rows={14}
            className="w-full bg-[#0b0f19] border border-[#1e293b] rounded-lg p-3 text-sm text-slate-100 font-mono focus:outline-none focus:border-sky-500 transition-colors resize-none"
            placeholder="Type or paste any Telegram signal..."
          />
        </div>

        {/* Right: Live Signal Decision Card */}
        <div className="lg:col-span-6 space-y-4">
          {previewSignalItem ? (
            <div className="space-y-3">
              <div className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
                Live Decision Output
              </div>
              <SignalDecisionCard signal={previewSignalItem} />
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center border border-dashed border-[#1e293b] rounded-xl text-slate-500 text-xs">
              <Terminal className="h-8 w-8 mb-2 opacity-50" />
              <span>Type or choose an example on the left to test the decision card.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
