const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface Holding {
    id: number;
    ticker: string;
    quantity: number;
    average_price: number;
    country: string;
    benchmark_symbol: string;
    created_at: string;
}

export interface HoldingCreate {
    ticker: string;
    quantity: number;
    average_price: number;
    country: string;
    benchmark_symbol: string;
}

export interface Prediction {
    ticker: string;
    score: number;
    recommendation: 'Buy' | 'Hold' | 'Sell';
    confidence: number;
}

export interface FeatureImpact {
    feature: string;
    impact: number;
    value: number;
}

export interface Explanation {
    ticker: string;
    top_positive: FeatureImpact[];
    top_negative: FeatureImpact[];
    base_value: number;
}

export interface EquityPoint {
    date: string;
    strategy: number;
    benchmark: number;
}

export interface BacktestMetrics {
    total_return: number;
    benchmark_total_return: number;
    cagr: number;
    benchmark_cagr: number;
    sharpe_ratio: number;
    max_drawdown: number;
    win_rate: number;
    volatility: number;
}

export interface RebalanceStep {
    date: string;
    top_assets: string[];
}

export interface BacktestResult {
    equity_curve: EquityPoint[];
    final_value: number;
    benchmark_final_value: number;
    metrics: BacktestMetrics;
    rebalance_history: RebalanceStep[];
}

export interface RiskMetrics {
    total_value_usd: number;
    total_value_inr: number;
    exchange_rate: number;
    holdings: Array<{
        ticker: string;
        quantity: number;
        price: number;
        value_native: number;
        currency: string;
        sector: string;
        allocation: number;
    }>;
    max_allocation: {
        ticker: string;
        percentage: number;
        warning: boolean;
    };
    sector_exposure: Record<string, number>;
    sector_warnings: string[];
    correlation_matrix: Record<string, Record<string, number>>;
    asset_drawdowns: Record<string, number>;
    drawdown_alerts: string[];
}

export const fetchHoldings = async (): Promise<Holding[]> => {
    const response = await fetch(`${API_URL}/holdings/`);
    if (!response.ok) throw new Error('Failed to fetch holdings');
    return response.json();
};

export const fetchPrediction = async (ticker: string): Promise<Prediction> => {
    const response = await fetch(`${API_URL}/predict/${ticker}`);
    if (!response.ok) throw new Error('Failed to fetch prediction');
    return response.json();
};

export const createHolding = async (holding: HoldingCreate): Promise<Holding> => {
    const response = await fetch(`${API_URL}/holdings/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(holding),
    });
    if (!response.ok) throw new Error('Failed to create holding');
    return response.json();
};

export const deleteHolding = async (id: number): Promise<void> => {
    const response = await fetch(`${API_URL}/holdings/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete holding');
};

export const runBacktest = async (startDate: string, topN: number): Promise<BacktestResult> => {
    const params = new URLSearchParams({ start_date: startDate, top_n: String(topN) });
    const response = await fetch(`${API_URL}/backtest/run?${params.toString()}`, {
        method: 'POST',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Backtest failed' }));
        throw new Error(err.detail || 'Backtest failed');
    }
    return response.json();
};

export const fetchExplanation = async (ticker: string): Promise<Explanation> => {
    const response = await fetch(`${API_URL}/explain/${ticker}`);
    if (!response.ok) throw new Error('Failed to fetch explanation');
    return response.json();
};

export const fetchRiskMetrics = async (): Promise<RiskMetrics> => {
    const response = await fetch(`${API_URL}/risk/metrics`);
    if (!response.ok) throw new Error('Failed to fetch risk metrics');
    return response.json();
};
