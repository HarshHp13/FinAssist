'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
} from 'recharts';
import { fetchFeatures, fetchPrediction, Feature, Prediction } from '@/lib/api';

// ─── Helpers ────────────────────────────────────────────────────────────────

function pct(n?: number) {
    if (n === undefined || n === null) return 'N/A';
    return `${(n * 100).toFixed(2)}%`;
}

function fmt(n?: number, decimals = 2) {
    if (n === undefined || n === null) return 'N/A';
    return n.toFixed(decimals);
}

function shortDate(iso: string) {
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', year: '2-digit' });
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function MetricCard({
    label,
    value,
    sub,
    positive,
    tooltip,
}: {
    label: string;
    value: string;
    sub?: string;
    positive?: boolean;
    tooltip?: string;
}) {
    const color =
        positive === undefined
            ? 'text-white'
            : positive
                ? 'text-emerald-400'
                : 'text-rose-400';

    return (
        <div className="bg-white/5 border border-white/10 rounded-2xl p-5 flex flex-col gap-1 hover:bg-white/10 transition-colors group relative">
            <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                    {label}
                </span>
                {tooltip && (
                    <div className="group/tip relative flex items-center">
                        <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-3 w-56 p-3 bg-slate-900 text-[11px] leading-relaxed text-slate-300 rounded-xl shadow-2xl border border-white/10 opacity-0 group-hover/tip:opacity-100 pointer-events-none transition-all scale-95 group-hover/tip:scale-100 z-50">
                            {tooltip}
                            <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-3 h-3 bg-slate-900 border-r border-b border-white/10 rotate-45"></div>
                        </div>
                    </div>
                )}
            </div>
            <span className={`text-2xl font-bold ${color}`}>{value}</span>
            {sub && <span className="text-xs text-slate-500 font-medium">{sub}</span>}
        </div>
    );
}

function CustomTooltip({ active, payload, label }: any) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-slate-900/90 border border-white/10 rounded-xl p-3 text-sm shadow-xl">
            <p className="font-semibold text-slate-300 mb-2">{label}</p>
            {payload.map((p: any) => (
                <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
                    {p.name}: <span className="text-white">{(Number(p.value) * 100).toFixed(2)}%</span>
                </p>
            ))}
        </div>
    );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function MFDetailPage() {
    const params = useParams();
    const ticker = params.ticker as string;

    const [features, setFeatures] = useState<Feature[]>([]);
    const [prediction, setPrediction] = useState<Prediction | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (ticker) {
            loadData();
        }
    }, [ticker]);

    const loadData = async () => {
        setLoading(true);
        try {
            const [featData, predData] = await Promise.all([
                fetchFeatures(ticker),
                fetchPrediction(ticker)
            ]);
            // Features come in descending order (latest first), reverse for chart
            setFeatures(featData.reverse());
            setPrediction(predData);
        } catch (e: any) {
            setError(e.message || 'Failed to load fund data');
        } finally {
            setLoading(false);
        }
    };

    const latest = features.length > 0 ? features[features.length - 1] : null;

    const chartData = features.filter(f => f.cagr_3y !== null).map(f => ({
        date: shortDate(f.date),
        '3Y Rolling Return': f.cagr_3y,
        '1Y Rolling Return': f.cagr_1y,
    }));

    if (loading) return (
        <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
            <div className="animate-pulse text-blue-500 font-bold">Loading Fund Analytics...</div>
        </div>
    );

    if (error) return (
        <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-8">
            <div className="bg-rose-500/10 border border-rose-500/30 p-6 rounded-2xl text-rose-400 max-w-md text-center">
                <h2 className="text-xl font-bold mb-2">Error</h2>
                <p className="text-sm mb-4">{error}</p>
                <Link href="/" className="text-blue-400 underline uppercase text-xs font-bold">Return to Dashboard</Link>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-zinc-950 text-white font-sans p-8">
            <div className="max-w-6xl mx-auto space-y-10">
                <header className="flex items-center justify-between">
                    <div>
                        <Link href="/" className="text-zinc-500 hover:text-white text-sm transition-colors mb-4 block">
                            ← Back to Portfolio
                        </Link>
                        <h1 className="text-4xl font-extrabold tracking-tighter">
                            {ticker} <span className="text-blue-500">Analytics</span>
                        </h1>
                        <p className="text-zinc-400 mt-1">Detailed performance metrics and AI scoring for this mutual fund.</p>
                    </div>
                    {prediction && (
                        <div className="bg-zinc-900 border border-zinc-800 p-4 rounded-2xl flex items-center gap-6">
                            <div className="text-center">
                                <span className={`text-4xl font-black ${prediction.score > 70 ? 'text-emerald-400' : prediction.score > 30 ? 'text-amber-400' : 'text-rose-400'}`}>
                                    {prediction.score.toFixed(0)}
                                </span>
                                <div className="text-[10px] text-zinc-500 uppercase font-black tracking-widest mt-1">AI Score</div>
                            </div>
                            <div className="h-10 w-px bg-zinc-800"></div>
                            <div className="text-center">
                                <span className={`text-xl font-bold ${prediction.recommendation === 'Buy' ? 'text-emerald-400' : prediction.recommendation === 'Hold' ? 'text-amber-400' : 'text-rose-400'}`}>
                                    {prediction.recommendation}
                                </span>
                                <div className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest mt-1">Rec</div>
                            </div>
                        </div>
                    )}
                </header>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 text-white">
                    <MetricCard
                        label="CAGR (3Y)"
                        value={pct(latest?.cagr_3y)}
                        positive={(latest?.cagr_3y || 0) > 0.12}
                        tooltip="Compound Annual Growth Rate over the last 3 years."
                    />
                    <MetricCard
                        label="CAGR (1Y)"
                        value={pct(latest?.cagr_1y)}
                        positive={(latest?.cagr_1y || 0) > 0.15}
                        tooltip="Compound Annual Growth Rate over the last 1 year."
                    />
                    <MetricCard
                        label="Alpha"
                        value={pct(latest?.alpha)}
                        positive={(latest?.alpha || 0) > 0}
                        sub="Relative to Benchmark"
                        tooltip="Excess return above the benchmark index."
                    />
                    <MetricCard
                        label="Sharpe Ratio"
                        value={fmt(latest?.sharpe)}
                        positive={(latest?.sharpe || 0) > 1.0}
                        sub="Risk-adjusted Return"
                        tooltip="Reward-to-volatility ratio. High values indicate better risk-adjusted performance."
                    />
                    <MetricCard
                        label="Consistency"
                        value={pct(latest?.rolling_consistency)}
                        positive={(latest?.rolling_consistency || 0) > 0.6}
                        sub="Rolling Outperformance"
                        tooltip="Frequency of beating the benchmark on a rolling basis."
                    />
                    <MetricCard
                        label="Expense Ratio"
                        value={pct(latest?.expense_ratio)}
                        positive={false}
                        tooltip="Annual fee charged by the fund."
                    />
                </div>

                <div className="bg-zinc-900 border border-zinc-800 rounded-3xl p-8">
                    <h3 className="text-xl font-bold mb-8 flex items-center gap-3">
                        Rolling Returns <span className="text-zinc-500 font-normal text-sm">— Strategy Insight</span>
                    </h3>
                    <div className="h-[400px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: '#71717a', fontSize: 12 }}
                                    minTickGap={30}
                                />
                                <YAxis
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fill: '#71717a', fontSize: 12 }}
                                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                                <Line
                                    type="monotone"
                                    dataKey="3Y Rolling Return"
                                    stroke="#3b82f6"
                                    strokeWidth={3}
                                    dot={false}
                                    activeDot={{ r: 6, strokeWidth: 0 }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey="1Y Rolling Return"
                                    stroke="#ec4899"
                                    strokeWidth={2}
                                    dot={false}
                                    strokeDasharray="5 5"
                                    activeDot={{ r: 4, strokeWidth: 0 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
}
