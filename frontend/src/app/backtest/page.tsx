'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
    ResponsiveContainer,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
} from 'recharts';
import { runBacktest, BacktestResult } from '@/lib/api';

// ─── helpers ────────────────────────────────────────────────────────────────

function fmt(n: number, decimals = 2) {
    return n.toFixed(decimals);
}

function pct(n: number) {
    return `${(n * 100).toFixed(2)}%`;
}

function shortDate(iso: string) {
    return iso.slice(0, 7); // YYYY-MM
}

// ─── sub-components ─────────────────────────────────────────────────────────

function MetricCard({
    label,
    value,
    sub,
    positive,
}: {
    label: string;
    value: string;
    sub?: string;
    positive?: boolean;
}) {
    const color =
        positive === undefined
            ? 'text-white'
            : positive
                ? 'text-emerald-400'
                : 'text-rose-400';

    return (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-1 hover:bg-white/10 transition-colors">
            <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                {label}
            </span>
            <span className={`text-2xl font-bold ${color}`}>{value}</span>
            {sub && <span className="text-xs text-slate-500">{sub}</span>}
        </div>
    );
}

// ─── Custom Tooltip ──────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-slate-900/90 border border-white/10 rounded-xl p-3 text-sm shadow-xl">
            <p className="font-semibold text-slate-300 mb-2">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
                    {p.name}: <span className="text-white">{Number(p.value).toFixed(2)}</span>
                </p>
            ))}
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function BacktestPage() {
    const [startDate, setStartDate] = useState('2022-01-01');
    const [topN, setTopN] = useState(5);
    const [result, setResult] = useState<BacktestResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleRun = async () => {
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await runBacktest(startDate, topN);
            setResult(data);
        } catch (e: any) {
            setError(e.message || 'Unknown error');
        } finally {
            setLoading(false);
        }
    };

    const chartData = result?.equity_curve.map((pt) => ({
        date: shortDate(pt.date),
        Strategy: parseFloat(pt.strategy.toFixed(4)),
        Benchmark: parseFloat(pt.benchmark.toFixed(4)),
    }));

    const m = result?.metrics;

    return (
        <div
            className="min-h-screen text-white font-sans"
            style={{
                background:
                    'linear-gradient(135deg, #0d1117 0%, #0f1f35 50%, #0d1117 100%)',
            }}
        >
            {/* ── Top Nav ── */}
            <nav className="border-b border-white/10 px-8 py-4 flex items-center justify-between">
                <Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">
                    ← Portfolio
                </Link>
                <h1 className="text-lg font-bold tracking-tight">
                    Fin<span className="text-blue-400">Assist</span>{' '}
                    <span className="text-slate-400 font-normal">/ Backtesting</span>
                </h1>
                <span className="text-xs text-slate-600">Loop 5 · PR 5.3</span>
            </nav>

            <main className="max-w-6xl mx-auto px-6 py-10 space-y-10">
                {/* ── Hero ── */}
                <section>
                    <h2 className="text-3xl font-extrabold tracking-tight mb-1">
                        Strategy{' '}
                        <span className="bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
                            Backtest
                        </span>
                    </h2>
                    <p className="text-slate-400 text-sm">
                        Walk-forward simulation with monthly retraining · Top-N asset selection · 3-month hold
                    </p>
                </section>

                {/* ── Controls ── */}
                <section className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-wrap gap-6 items-end">
                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                            Start Date
                        </label>
                        <input
                            id="backtest-start-date"
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="bg-slate-800 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                        />
                    </div>

                    <div className="flex flex-col gap-1">
                        <label className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                            Top N Assets
                        </label>
                        <input
                            id="backtest-top-n"
                            type="number"
                            min={1}
                            max={20}
                            value={topN}
                            onChange={(e) => setTopN(Number(e.target.value))}
                            className="bg-slate-800 border border-white/10 rounded-lg px-4 py-2 text-white text-sm w-24 focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                        />
                    </div>

                    <button
                        id="run-backtest-btn"
                        onClick={handleRun}
                        disabled={loading}
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold px-6 py-2 rounded-lg transition-colors shadow-lg shadow-blue-600/20"
                    >
                        {loading ? (
                            <>
                                <svg
                                    className="animate-spin h-4 w-4"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth={2}
                                >
                                    <path
                                        strokeLinecap="round"
                                        d="M12 2a10 10 0 100 20A10 10 0 0012 2z"
                                        strokeDasharray="60"
                                        strokeDashoffset="45"
                                    />
                                </svg>
                                Running…
                            </>
                        ) : (
                            '▶ Run Backtest'
                        )}
                    </button>
                </section>

                {/* ── Error ── */}
                {error && (
                    <div className="bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-2xl p-4 text-sm">
                        ⚠ {error}
                    </div>
                )}

                {/* ── Results ── */}
                {result && m && (
                    <>
                        {/* KPI grid */}
                        <section>
                            <h3 className="text-base font-semibold text-slate-300 mb-4">Performance Metrics</h3>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <MetricCard
                                    label="Strategy CAGR"
                                    value={pct(m.cagr)}
                                    sub={`Benchmark: ${pct(m.benchmark_cagr)}`}
                                    positive={m.cagr > 0}
                                />
                                <MetricCard
                                    label="Total Return"
                                    value={pct(m.total_return)}
                                    sub={`Benchmark: ${pct(m.benchmark_total_return)}`}
                                    positive={m.total_return > 0}
                                />
                                <MetricCard
                                    label="Sharpe Ratio"
                                    value={fmt(m.sharpe_ratio)}
                                    sub="Risk-adjusted (annualised)"
                                    positive={m.sharpe_ratio > 1}
                                />
                                <MetricCard
                                    label="Max Drawdown"
                                    value={pct(m.max_drawdown)}
                                    sub="Peak-to-trough decline"
                                    positive={m.max_drawdown > -0.15}
                                />
                                <MetricCard
                                    label="Win Rate"
                                    value={pct(m.win_rate)}
                                    sub="% months with positive return"
                                    positive={m.win_rate > 0.5}
                                />
                                <MetricCard
                                    label="Final Portfolio"
                                    value={`$${result.final_value.toFixed(2)}`}
                                    sub="Normalised from $100"
                                />
                                <MetricCard
                                    label="Benchmark Final"
                                    value={`$${result.benchmark_final_value.toFixed(2)}`}
                                    sub="S&P 500 (^GSPC)"
                                />
                                <MetricCard
                                    label="Alpha"
                                    value={pct(m.cagr - m.benchmark_cagr)}
                                    sub="Strategy vs Benchmark CAGR"
                                    positive={m.cagr >= m.benchmark_cagr}
                                />
                            </div>
                        </section>

                        {/* Equity curve chart */}
                        <section className="bg-white/5 border border-white/10 rounded-2xl p-6">
                            <h3 className="text-base font-semibold text-slate-300 mb-6">
                                Equity Curve — Strategy vs Benchmark
                            </h3>
                            <ResponsiveContainer width="100%" height={380}>
                                <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
                                    <defs>
                                        <linearGradient id="stratGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
                                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="benchGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
                                            <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fill: '#64748b', fontSize: 11 }}
                                        tickLine={false}
                                        axisLine={false}
                                    />
                                    <YAxis
                                        tick={{ fill: '#64748b', fontSize: 11 }}
                                        tickLine={false}
                                        axisLine={false}
                                        tickFormatter={(v) => `$${v.toFixed(0)}`}
                                        width={55}
                                    />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend
                                        wrapperStyle={{ color: '#94a3b8', fontSize: 13, paddingTop: 12 }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="Strategy"
                                        stroke="#3b82f6"
                                        strokeWidth={2.5}
                                        fill="url(#stratGrad)"
                                        dot={false}
                                        activeDot={{ r: 5, strokeWidth: 0 }}
                                    />
                                    <Area
                                        type="monotone"
                                        dataKey="Benchmark"
                                        stroke="#94a3b8"
                                        strokeWidth={1.5}
                                        fill="url(#benchGrad)"
                                        strokeDasharray="4 4"
                                        dot={false}
                                        activeDot={{ r: 4, strokeWidth: 0 }}
                                    />
                                </AreaChart>
                            </ResponsiveContainer>
                        </section>

                        {/* Rebalance History */}
                        <section className="bg-white/5 border border-white/10 rounded-2xl p-6">
                            <h3 className="text-base font-semibold text-slate-300 mb-6">
                                Monthly Rebalance History
                            </h3>
                            <div className="overflow-x-auto">
                                <table className="w-full text-left text-sm">
                                    <thead>
                                        <tr className="border-b border-white/5 text-slate-500 font-medium">
                                            <th className="pb-3 px-2">Date</th>
                                            <th className="pb-3 px-2">Selected Assets (Top {topN})</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {result.rebalance_history.slice().reverse().map((step, idx) => (
                                            <tr key={idx} className="hover:bg-white/5 transition-colors">
                                                <td className="py-3 px-2 text-slate-300 font-mono">
                                                    {shortDate(step.date)}
                                                </td>
                                                <td className="py-3 px-2">
                                                    <div className="flex flex-wrap gap-2">
                                                        {step.top_assets.length > 0 ? (
                                                            step.top_assets.map(ticker => (
                                                                <span key={ticker} className="bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20 font-bold">
                                                                    {ticker}
                                                                </span>
                                                            ))
                                                        ) : (
                                                            <span className="text-slate-600 italic">No assets selected (insufficient data)</span>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>
                    </>
                )}

                {/* ── Empty state ── */}
                {!result && !loading && !error && (
                    <div className="flex flex-col items-center justify-center py-20 text-slate-600 gap-3">
                        <svg
                            className="w-12 h-12 opacity-40"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={1.2}
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M3 17l4-8 4 5 3-3 5 7M3 21h18"
                            />
                        </svg>
                        <p className="text-sm">Configure parameters above and click <strong>Run Backtest</strong> to see results.</p>
                    </div>
                )}
            </main>
        </div>
    );
}
