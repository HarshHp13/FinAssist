from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from models import Price, Feature, MacroData
from lightgbm import LGBMClassifier
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BacktestService:
    def __init__(self, db: Session):
        self.db = db

    def run_walk_forward_backtest(self, start_date_str="2022-01-01", top_n=5, hold_period_months=3):
        """
        PR 5.1: Walk-Forward Backtest Engine
        - Monthly retrain
        - Select top N assets
        - Hold for 3 months
        - Track performance
        """
        start_date = pd.to_datetime(start_date_str).tz_localize('UTC')
        
        # 1. Load all features and prices into memory for faster processing
        # This is okay for a manageable number of tickers and dates
        query = select(Feature).filter(Feature.rsi.isnot(None))
        features_db = self.db.execute(query).scalars().all()
        
        if not features_db:
            return {"error": "No features found in database. Run feature generation first."}
            
        df_features = pd.DataFrame([{
            'ticker': f.ticker,
            'date': f.date if f.date.tzinfo else pd.to_datetime(f.date).tz_localize('UTC'),
            'rsi': f.rsi,
            'macd': f.macd,
            'macd_signal': f.macd_signal,
            'dma_50': f.dma_50,
            'dma_200': f.dma_200,
            'momentum_1m': f.momentum_1m,
            'momentum_3m': f.momentum_3m,
            'momentum_6m': f.momentum_6m,
            'volatility_30d': f.volatility_30d,
            'drawdown': f.drawdown,
            'relative_strength': f.relative_strength,
            'rolling_outperformance': f.rolling_outperformance,
            'beta': f.beta,
            'target_class': f.target_class
        } for f in features_db])
        
        df_features['date'] = pd.to_datetime(df_features['date'])
        
        # Load prices
        price_query = select(Price)
        prices_db = self.db.execute(price_query).scalars().all()
        df_prices = pd.DataFrame([{
            'ticker': p.ticker,
            'date': p.date if p.date.tzinfo else pd.to_datetime(p.date).tz_localize('UTC'),
            'close': p.close
        } for p in prices_db])
        df_prices['date'] = pd.to_datetime(df_prices['date'])
        
        # 2. Define simulation dates (Monthly steps)
        all_dates = sorted(df_features['date'].unique())
        backtest_dates = [d for d in all_dates if d >= start_date]
        
        if not backtest_dates:
            return {"error": f"No data found after {start_date_str}"}

        # Group by month
        monthly_dates = pd.Series(backtest_dates).groupby(pd.Series(backtest_dates).dt.to_period('M')).first()
        simulation_points = monthly_dates.tolist()
        
        equity_curve = []
        portfolio_value = 100.0  # Normalized start
        benchmark_value = 100.0
        
        # Sleeves for 3-month overlap: each sleeve is a dict {holdings: {ticker: weight}, value: float}
        # Initialize with cash
        sleeves: List[Dict[str, Any]] = [
            {'holdings': {}, 'value': portfolio_value / hold_period_months}
            for _ in range(hold_period_months)
        ]
        
        equity_curve.append({
            "date": simulation_points[0].isoformat(),
            "strategy": portfolio_value,
            "benchmark": benchmark_value
        })
        
        feature_cols = [
            'rsi', 'macd', 'macd_signal', 'dma_50', 'dma_200', 
            'momentum_1m', 'momentum_3m', 'momentum_6m', 
            'volatility_30d', 'drawdown', 'relative_strength', 
            'rolling_outperformance', 'beta'
        ]

        # Determine benchmark symbol
        # Just pick one for simplicity or use a major index
        benchmark_symbol = "^GSPC" # Default

        rebalance_history = []

        for i in range(len(simulation_points) - 1):
            current_date = simulation_points[i]
            next_date = simulation_points[i+1]
            sleeve_idx = i % hold_period_months
            
            logger.info(f"Step {i}: {current_date} to {next_date}. Rebalancing sleeve {sleeve_idx}")
            
            # 1. Update existing sleeves values to current_date
            # (Wait, we need to know the return from last next_date to this current_date)
            # Actually, we update all sleeves EVERY month to track total portfolio value.
            
            # 2. Retrain and get top N
            train_mask = df_features['date'] <= (current_date - pd.Timedelta(days=90))
            train_df = df_features[train_mask].dropna(subset=feature_cols + ['target_class'])
            
            top_assets = []
            if len(train_df) >= 50:
                model = LGBMClassifier(n_estimators=50, learning_rate=0.1, verbose=-1, random_state=42)
                model.fit(train_df[feature_cols], train_df['target_class'])
                
                pred_mask = df_features['date'] == current_date
                pred_df = df_features[pred_mask].dropna(subset=feature_cols)
                
                if not pred_df.empty:
                    probs = model.predict_proba(pred_df[feature_cols])[:, 1]
                    pred_df['prob'] = probs
                    top_assets = pred_df.sort_values(by='prob', ascending=False).head(top_n)['ticker'].tolist()

            # Record rebalance
            rebalance_history.append({
                "date": current_date.isoformat(),
                "top_assets": top_assets
            })

            # 3. Liquidate old sleeve and re-allocate 1/3 of total portfolio to new top N
            sleeve_value = portfolio_value / hold_period_months
            if top_assets:
                sleeves[sleeve_idx] = {
                    'holdings': {ticker: 1.0 / len(top_assets) for ticker in top_assets},
                    'value': sleeve_value
                }
            else:
                # If no top assets (e.g. no data), hold cash in this sleeve
                sleeves[sleeve_idx] = {
                    'holdings': {},
                    'value': sleeve_value
                }

            # 4. Step to next_date: Calculate returns for ALL active sleeves
            new_portfolio_value = 0
            for s in sleeves:
                ret = self._get_portfolio_return(s['holdings'], current_date, next_date, df_prices)
                s['value'] = s['value'] * (1 + ret)
                new_portfolio_value += s['value']
            
            portfolio_value = new_portfolio_value
            
            # 5. Benchmark update
            bench_ret = self._get_benchmark_return(benchmark_symbol, current_date, next_date)
            benchmark_value *= (1 + bench_ret)
            
            equity_curve.append({
                "date": next_date.isoformat(),
                "strategy": portfolio_value,
                "benchmark": benchmark_value
            })

        metrics = self._calculate_metrics(equity_curve)

        return {
            "equity_curve": equity_curve,
            "final_value": portfolio_value,
            "benchmark_final_value": benchmark_value,
            "metrics": metrics,
            "rebalance_history": rebalance_history
        }

    def _get_portfolio_return(self, holdings, start_date, end_date, df_prices):
        if not holdings:
            return 0.0
            
        total_ret = 0
        for ticker, weight in holdings.items():
            p_start = df_prices[(df_prices['ticker'] == ticker) & (df_prices['date'] == start_date)]
            p_end = df_prices[(df_prices['ticker'] == ticker) & (df_prices['date'] == end_date)]
            
            if not p_start.empty and not p_end.empty:
                ret = (p_end.iloc[0]['close'] / p_start.iloc[0]['close']) - 1
                total_ret += ret * weight
        return total_ret

    def _get_benchmark_return(self, symbol, start_date, end_date):
        # Fetch from MacroData
        query = select(MacroData).filter(
            and_(
                MacroData.symbol == symbol,
                MacroData.date >= start_date,
                MacroData.date <= end_date
            )
        ).order_by(MacroData.date.asc())
        
        results = self.db.execute(query).scalars().all()
        if len(results) >= 2:
            # Match the dates as closely as possible
            # For simplicity, just use first and last in range
            start_val = results[0].value
            end_val = results[-1].value
            return (end_val / start_val) - 1
        return 0.0

    def _calculate_metrics(self, equity_curve: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not equity_curve or len(equity_curve) < 2:
            return {}
            
        df = pd.DataFrame(equity_curve)
        df['date'] = pd.to_datetime(df['date'])
        
        # Monthly returns
        df['strat_ret'] = df['strategy'].pct_change().fillna(0)
        df['bench_ret'] = df['benchmark'].pct_change().fillna(0)
        
        # Summary metrics
        start_val = df['strategy'].iloc[0]
        end_val = df['strategy'].iloc[-1]
        bench_start = df['benchmark'].iloc[0]
        bench_end = df['benchmark'].iloc[-1]
        
        total_days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
        years = max(total_days / 365.25, 1/12)
        
        cagr = (end_val / start_val) ** (1 / years) - 1
        bench_cagr = (bench_end / bench_start) ** (1 / years) - 1
        
        # Sharpe Ratio (Monthly)
        mean_monthly_ret = df['strat_ret'].mean()
        std_monthly_ret = df['strat_ret'].std()
        sharpe = (mean_monthly_ret / std_monthly_ret) * np.sqrt(12) if std_monthly_ret > 0 else 0
        
        # Max Drawdown
        rolling_max = df['strategy'].cummax()
        drawdowns = (df['strategy'] - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        # Win Rate
        win_rate = (df['strat_ret'] > 0).mean()
        
        # Volatility (Annualized)
        volatility = df['strat_ret'].std() * np.sqrt(12) if df['strat_ret'].std() > 0 else 0
        
        return {
            "total_return": float((end_val / start_val) - 1),
            "benchmark_total_return": float((bench_end / bench_start) - 1),
            "cagr": float(cagr),
            "benchmark_cagr": float(bench_cagr),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "win_rate": float(win_rate),
            "volatility": float(volatility)
        }
