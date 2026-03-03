import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from models import Price, Feature, MacroData
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class FeatureEngineer:
    def __init__(self, db: Session):
        self.db = db

    def generate_features(self, ticker: str):
        """
        PR 3.1, 3.2, 3.3: Generate all ML features and targets
        - RSI
        - MACD
        - 50/200 DMA
        - Momentum (1m, 3m, 6m)
        - Volatility (30d)
        - Drawdown
        """
        logger.info(f"Generating features for {ticker}...")
        
        # Load prices from DB
        prices = self.db.query(Price).filter(Price.ticker == ticker).order_by(Price.date.asc()).all()
        if not prices:
            logger.warning(f"No price data found for {ticker}")
            return False

        df = pd.DataFrame([{
            'date': p.date,
            'close': p.close
        } for p in prices])
        
        df.set_index('date', inplace=True)

        # 1. RSI (14 days)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 2. MACD (12, 26, 9)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # 3. 50/200 DMA
        df['dma_50'] = df['close'].rolling(window=50).mean()
        df['dma_200'] = df['close'].rolling(window=200).mean()

        # 4. Momentum (1m=21d, 3m=63d, 6m=126d)
        df['momentum_1m'] = df['close'] / df['close'].shift(21) - 1
        df['momentum_3m'] = df['close'] / df['close'].shift(63) - 1
        df['momentum_6m'] = df['close'] / df['close'].shift(126) - 1

        # 5. Volatility (30d annualized)
        df['volatility_30d'] = df['close'].pct_change().rolling(window=30).std() * np.sqrt(252)

        # 6. Drawdown
        rolling_max = df['close'].rolling(window=252, min_periods=1).max()
        df['drawdown'] = (df['close'] / rolling_max) - 1

        # PR 3.2: Relative Strength Features
        benchmark_symbol = "^NSEI" if ticker.endswith(".NS") else "^GSPC"
        index_prices = self.db.query(MacroData).filter(MacroData.symbol == benchmark_symbol).order_by(MacroData.date.asc()).all()
        
        if index_prices:
            idx_df = pd.DataFrame([{'date': p.date, 'index_close': p.value} for p in index_prices])
            idx_df.set_index('date', inplace=True)
            
            # Merge with master df
            df = df.join(idx_df, how='left')
            
            # Forward fill missing index prices (e.g. if stock traded but index didn't)
            df['index_close'] = df['index_close'].ffill()
            
            # 7. Relative Strength (Stock / Index)
            df['relative_strength'] = df['close'] / df['index_close']
            
            # 8. Rolling Outperformance (90d)
            # (Stock return 90d) - (Index return 90d)
            stock_ret_90 = df['close'].pct_change(90)
            index_ret_90 = df['index_close'].pct_change(90)
            df['rolling_outperformance'] = stock_ret_90 - index_ret_90
            
            # 9. Beta (rolling 252d)
            stock_returns = df['close'].pct_change()
            index_returns = df['index_close'].pct_change()
            rolling_cov = stock_returns.rolling(window=252).cov(index_returns)
            rolling_var = index_returns.rolling(window=252).var()
            df['beta'] = rolling_cov / rolling_var
        else:
            df['relative_strength'] = None
            df['rolling_outperformance'] = None
            df['beta'] = None

        # Forward 90-day return: (Price at T+90 / Price at T) - 1
        # Shift -90 to bring future price to current row
        df['target_return_90d'] = df['close'].shift(-90) / df['close'] - 1
        
        # Adjust threshold: 10% for India, 0% for US/others as per PRD
        threshold = 0.10 if ticker.endswith(".NS") else 0.0
        df['target_class'] = (df['target_return_90d'] > threshold).astype(float)
        # Ensure the last 90 rows have NaN targets as we don't know the future
        df.loc[df['target_return_90d'].isna(), 'target_class'] = np.nan

        # Store in DB
        new_records = 0
        for date, row in df.iterrows():
            # Skip if critical features are NaN (usually at the start of the series)
            if pd.isna(row['rsi']) and pd.isna(row['dma_50']):
                continue

            existing = self.db.query(Feature).filter(
                Feature.ticker == ticker,
                Feature.date == date
            ).first()

            # Helper to convert to float or None
            to_float = lambda val: float(val) if not pd.isna(val) else None

            if existing:
                # Update existing record
                existing.rsi = to_float(row['rsi'])
                existing.macd = to_float(row['macd'])
                existing.macd_signal = to_float(row['macd_signal'])
                existing.dma_50 = to_float(row['dma_50'])
                existing.dma_200 = to_float(row['dma_200'])
                existing.momentum_1m = to_float(row['momentum_1m'])
                existing.momentum_3m = to_float(row['momentum_3m'])
                existing.momentum_6m = to_float(row['momentum_6m'])
                existing.volatility_30d = to_float(row['volatility_30d'])
                existing.drawdown = to_float(row['drawdown'])
                
                # PR 3.2
                existing.relative_strength = to_float(row.get('relative_strength'))
                existing.rolling_outperformance = to_float(row.get('rolling_outperformance'))
                existing.beta = to_float(row.get('beta'))
                
                # PR 3.3
                existing.target_return_90d = to_float(row.get('target_return_90d'))
                existing.target_class = int(row['target_class']) if not pd.isna(row.get('target_class')) else None
            else:
                new_feature = Feature(
                    ticker=ticker,
                    date=date,
                    rsi=to_float(row['rsi']),
                    macd=to_float(row['macd']),
                    macd_signal=to_float(row['macd_signal']),
                    dma_50=to_float(row['dma_50']),
                    dma_200=to_float(row['dma_200']),
                    momentum_1m=to_float(row['momentum_1m']),
                    momentum_3m=to_float(row['momentum_3m']),
                    momentum_6m=to_float(row['momentum_6m']),
                    volatility_30d=to_float(row['volatility_30d']),
                    drawdown=to_float(row['drawdown']),
                    relative_strength=to_float(row.get('relative_strength')),
                    rolling_outperformance=to_float(row.get('rolling_outperformance')),
                    beta=to_float(row.get('beta')),
                    target_return_90d=to_float(row.get('target_return_90d')),
                    target_class=int(row['target_class']) if not pd.isna(row.get('target_class')) else None
                )
                self.db.add(new_feature)
                new_records += 1

        self.db.commit()
        logger.info(f"Successfully processed features for {ticker}. New records: {new_records}")
        return True
