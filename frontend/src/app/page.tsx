'use client';

import { useState, useEffect, Fragment } from 'react';
import Link from 'next/link';
import { fetchHoldings, createHolding, deleteHolding, Holding, fetchExplanation, Explanation, fetchRiskMetrics, RiskMetrics } from '@/lib/api';

const getCurrencySymbol = (country: string) => country === 'IND' ? '₹' : '$';

const featureNames: Record<string, string> = {
  'rsi': 'Relative Strength Index (RSI)',
  'macd': 'MACD Momentum',
  'macd_signal': 'MACD Signal',
  'dma_50': '50-day Moving Average',
  'dma_200': '200-day Moving Average',
  'momentum_1m': '1-month momentum',
  'momentum_3m': '3-month momentum',
  'momentum_6m': '6-month momentum',
  'volatility_30d': '30-day volatility',
  'drawdown': 'Peak drawdown',
  'relative_strength': 'Relative index strength',
  'rolling_outperformance': '90-day outperformance',
  'beta': 'Market Beta'
};

const generateSummary = (explanation: Explanation, recommendation: string) => {
  const topPos = explanation.top_positive[0];
  const topNeg = explanation.top_negative[0];

  const posFeature = topPos ? featureNames[topPos.feature] || topPos.feature.replace(/_/g, ' ') : null;
  const negFeature = topNeg ? featureNames[topNeg.feature] || topNeg.feature.replace(/_/g, ' ') : null;

  if (recommendation === 'Buy') {
    return `The Buy signal is primarily driven by strong ${posFeature}${topNeg ? `, which is currently outweighing concerns about ${negFeature}` : ''}. This suggests a favorable risk-reward profile based on recent price action and relative strength.`;
  } else if (recommendation === 'Sell') {
    return `The Sell signal is largely due to weak ${negFeature}${topPos ? `, despite some positive influence from ${posFeature}` : ''}. The model identifies significant downward pressure from these technical factors.`;
  } else {
    return `The Hold rating reflects a neutral stance where ${posFeature} and ${negFeature} are balanced. The model suggests waiting for a clearer trend to emerge before taking a position.`;
  }
};

export default function Home() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [country, setCountry] = useState('US');
  const [assetType, setAssetType] = useState('STOCK');
  const [predictions, setPredictions] = useState<Record<string, any>>({});
  const [explanations, setExplanations] = useState<Record<string, Explanation>>({});
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);

  useEffect(() => {
    loadHoldings();
    loadRiskMetrics();
  }, []);

  const loadHoldings = async () => {
    try {
      const data = await fetchHoldings();
      setHoldings(data);
      // Fetch predictions for all holdings
      data.forEach(h => fetchPredictionData(h.ticker));
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const loadRiskMetrics = async () => {
    try {
      const data = await fetchRiskMetrics();
      setRiskMetrics(data);
    } catch (error) {
      console.error('Failed to fetch risk metrics', error);
    }
  };

  const fetchPredictionData = async (ticker: string) => {
    try {
      const { fetchPrediction } = await import('@/lib/api');
      const pred = await fetchPrediction(ticker);
      setPredictions(prev => ({ ...prev, [ticker]: pred }));

      const expl = await fetchExplanation(ticker);
      setExplanations(prev => ({ ...prev, [ticker]: expl }));
    } catch (error) {
      console.error(`Failed to fetch data for ${ticker}`, error);
    }
  };

  const handleAddHolding = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const benchmark = country === 'IND' ? '^NSEI' : '^GSPC';
      await createHolding({
        ticker: ticker.toUpperCase(),
        quantity: parseFloat(quantity),
        average_price: parseFloat(price),
        country: country,
        benchmark_symbol: benchmark,
        asset_type: assetType,
      });
      setTicker('');
      setQuantity('');
      setPrice('');
      await loadHoldings();
      await loadRiskMetrics();
    } catch (error) {
      alert('Error adding holding');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteHolding(id);
      await loadHoldings();
      await loadRiskMetrics();
    } catch (error) {
      alert('Error deleting holding');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-zinc-950 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <header className="mb-10 flex items-start justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 dark:text-zinc-50 tracking-tight">
              FinAssist <span className="text-blue-600">Portfolio</span>
            </h1>
            <p className="text-gray-600 dark:text-zinc-400 mt-2">Manage your stock holdings and get AI insights.</p>
          </div>
          <Link
            href="/backtest"
            className="mt-1 flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2 rounded-xl shadow-lg shadow-blue-500/20 transition-colors"
          >
            📈 Backtest Dashboard
          </Link>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Add Holding Form */}
          <div className="md:col-span-1 space-y-8">
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-zinc-800">
              <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-zinc-100">Add Holding</h2>
              <form onSubmit={handleAddHolding} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-1">Ticker</label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={(e) => setTicker(e.target.value)}
                    placeholder="e.g. AAPL"
                    className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-1">Quantity</label>
                    <input
                      type="number"
                      step="any"
                      value={quantity}
                      onChange={(e) => setQuantity(e.target.value)}
                      placeholder="0.00"
                      className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-1">Avg Price</label>
                    <input
                      type="number"
                      step="any"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      placeholder="0.00"
                      className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-1">Country</label>
                  <select
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                  >
                    <option value="US">United States (USD)</option>
                    <option value="IND">India (INR)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-zinc-300 mb-1">Asset Type</label>
                  <select
                    value={assetType}
                    onChange={(e) => setAssetType(e.target.value)}
                    className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-zinc-700 dark:bg-zinc-800 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none transition-all"
                  >
                    <option value="STOCK">Stock / ETF</option>
                    <option value="MF">Mutual Fund</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg transition-colors shadow-lg shadow-blue-500/20"
                >
                  Add Asset
                </button>
              </form>
            </div>

            {/* Portfolio Summary Card */}
            {riskMetrics && (
              <div className="bg-gradient-to-br from-zinc-900 to-black p-6 rounded-2xl shadow-xl border border-zinc-800 text-white">
                <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></span>
                  Portfolio Value
                </h3>
                <div className="space-y-4">
                  <div>
                    <div className="text-2xl font-black">${riskMetrics.total_value_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    <div className="text-[10px] text-zinc-500 uppercase font-semibold">USD (Base)</div>
                  </div>
                  <div className="pt-4 border-t border-zinc-800">
                    <div className="text-xl font-bold text-zinc-200">₹{riskMetrics.total_value_inr.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                    <div className="text-[10px] text-zinc-500 uppercase font-semibold">INR Equivalent</div>
                  </div>
                  <div className="text-[10px] text-zinc-600 italic mt-2">
                    Exchange Rate: 1 USD = ₹{riskMetrics.exchange_rate.toFixed(2)}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Holdings List */}
          <div className="md:col-span-2 bg-white dark:bg-zinc-900 p-6 rounded-2xl shadow-sm border border-gray-100 dark:border-zinc-800">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-zinc-100">Current Holdings</h2>
            {loading ? (
              <p className="text-gray-500">Loading portfolio...</p>
            ) : holdings.length === 0 ? (
              <div className="text-center py-10 text-gray-500">
                <p>Your portfolio is empty.</p>
                <p className="text-sm">Add your first holding to get started.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-gray-100 dark:border-zinc-800">
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase">Ticker</th>
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase">Region</th>
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase">Quantity</th>
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase text-right">Avg Price</th>
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase text-center">AI Score</th>
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase text-center">Rec</th>
                      <th className="pb-3 font-medium text-gray-500 text-sm uppercase text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50 dark:divide-zinc-800">
                    {holdings.map((h) => (
                      <Fragment key={h.id}>
                        <tr className="group border-b border-gray-50 dark:border-zinc-800">
                          <td className="py-4">
                            <div className="font-bold text-gray-900 dark:text-white">{h.ticker}</div>
                            <div className="text-[10px] text-gray-400 uppercase tracking-widest">{h.benchmark_symbol}</div>
                          </td>
                          <td className="py-4">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${h.country === 'IND' ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700'}`}>
                              {h.country}
                            </span>
                          </td>
                          <td className="py-4 text-gray-600 dark:text-zinc-300">{h.quantity}</td>
                          <td className="py-4 text-gray-600 dark:text-zinc-300 text-right">
                            {getCurrencySymbol(h.country)}{h.average_price.toFixed(2)}
                          </td>
                          <td className="py-4 text-center">
                            {predictions[h.ticker] ? (
                              <span className={`px-2 py-1 rounded-full text-xs font-bold ${predictions[h.ticker].score > 70 ? 'bg-green-100 text-green-700' :
                                predictions[h.ticker].score > 30 ? 'bg-yellow-100 text-yellow-700' :
                                  'bg-red-100 text-red-700'
                                }`}>
                                {predictions[h.ticker].score}
                              </span>
                            ) : (
                              <span className="text-gray-400 text-xs animate-pulse">...</span>
                            )}
                          </td>
                          <td className="py-4 text-center">
                            {predictions[h.ticker] ? (
                              <div className="flex flex-col items-center gap-1">
                                <span className={`text-sm font-semibold ${predictions[h.ticker].recommendation === 'Buy' ? 'text-green-500' :
                                  predictions[h.ticker].recommendation === 'Hold' ? 'text-yellow-500' :
                                    'text-red-500'
                                  }`}>
                                  {predictions[h.ticker].recommendation}
                                </span>
                                <button
                                  onClick={() => setExpandedTicker(expandedTicker === h.ticker ? null : h.ticker)}
                                  className="text-[10px] text-blue-500 hover:text-blue-700 hover:underline font-medium"
                                >
                                  {expandedTicker === h.ticker ? 'Close' : 'Why?'}
                                </button>
                              </div>
                            ) : (
                              <span className="text-gray-400 text-xs text-center block">Loading</span>
                            )}
                          </td>
                          <td className="py-4 text-right">
                            <button
                              onClick={() => handleDelete(h.id)}
                              className="text-red-500 hover:text-red-700 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                        {expandedTicker === h.ticker && explanations[h.ticker] && (
                          <tr className="bg-blue-50/30 dark:bg-blue-900/10">
                            <td colSpan={7} className="px-6 py-6 border-b border-blue-100/50 dark:border-blue-900/20">
                              <div className="flex flex-col gap-6">
                                <div className="flex items-center justify-between">
                                  <h3 className="text-sm font-bold text-gray-800 dark:text-zinc-200 uppercase tracking-wider">
                                    AI Decision Reasoning for {h.ticker}
                                  </h3>
                                  <div className="text-[10px] font-semibold px-2 py-1 bg-gray-100 dark:bg-zinc-800 rounded text-gray-500 dark:text-zinc-400">
                                    BASELINE PROB: {(explanations[h.ticker].base_value * 100).toFixed(1)}%
                                  </div>
                                </div>

                                {/* AI Summary Section (PR 8.3) */}
                                <div className="bg-white dark:bg-zinc-900 border border-blue-100 dark:border-blue-900/40 p-4 rounded-xl shadow-sm">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-blue-500 font-bold">✨</span>
                                    <h4 className="text-xs font-bold text-gray-900 dark:text-white uppercase tracking-tight">AI Interpretation</h4>
                                  </div>
                                  <p className="text-sm text-gray-600 dark:text-zinc-300 leading-relaxed italic">
                                    {generateSummary(explanations[h.ticker], predictions[h.ticker].recommendation)}
                                  </p>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                  {/* Positive Drivers */}
                                  <div>
                                    <h4 className="text-[10px] font-bold text-green-600 dark:text-green-400 mb-4 uppercase tracking-widest border-l-2 border-green-500 pl-2">Positive Drivers</h4>
                                    <div className="space-y-4">
                                      {explanations[h.ticker].top_positive.map((feat, idx) => (
                                        <div key={idx} className="flex flex-col gap-1.5 focus-within:ring-1 focus-within:ring-blue-500 rounded p-1">
                                          <div className="flex justify-between text-[11px]">
                                            <span className="text-gray-700 dark:text-zinc-300 font-medium capitalize">{feat.feature.replace(/_/g, ' ')}</span>
                                            <span className="text-green-600 font-bold">+{feat.impact.toFixed(3)}</span>
                                          </div>
                                          <div className="w-full bg-gray-200 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                                            <div
                                              className="bg-green-500 h-full rounded-full transition-all duration-500"
                                              style={{ width: `${Math.min(100, feat.impact * 100)}%` }}
                                            ></div>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>

                                  {/* Negative Drivers */}
                                  <div>
                                    <h4 className="text-[10px] font-bold text-red-600 dark:text-red-400 mb-4 uppercase tracking-widest border-l-2 border-red-500 pl-2">Negative Drivers</h4>
                                    <div className="space-y-4">
                                      {explanations[h.ticker].top_negative.map((feat, idx) => (
                                        <div key={idx} className="flex flex-col gap-1.5 rounded p-1">
                                          <div className="flex justify-between text-[11px]">
                                            <span className="text-gray-700 dark:text-zinc-300 font-medium capitalize">{feat.feature.replace(/_/g, ' ')}</span>
                                            <span className="text-red-600 font-bold">{feat.impact.toFixed(3)}</span>
                                          </div>
                                          <div className="w-full bg-gray-200 dark:bg-zinc-800 h-2 rounded-full overflow-hidden flex justify-end">
                                            <div
                                              className="bg-red-500 h-full rounded-full transition-all duration-500"
                                              style={{ width: `${Math.min(100, Math.abs(feat.impact) * 100)}%` }}
                                            ></div>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              </div>
            )
            }
          </div>
        </div>
      </div>
    </div>
  );
}
