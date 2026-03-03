import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import Holding, Price
import yfinance as yf
import logging

from services.currency_service import CurrencyService

logger = logging.getLogger(__name__)

class RiskService:
    def __init__(self, db: Session):
        self.db = db
        self.currency_service = CurrencyService(db)

    def get_portfolio_risk_metrics(self):
        """
        PR 6.3: Risk Controls
        - Max allocation rule
        - Sector exposure warning
        - Correlation matrix
        - Drawdown alert threshold
        - Multi-currency support (INR/USD)
        """
        holdings = self.db.query(Holding).all()
        if not holdings:
            return {"error": "No holdings found in portfolio."}

        tickers = [h.ticker for h in holdings]
        
        # 1. Fetch current prices and calculate values
        portfolio_data = []
        total_value_usd = 0
        
        for h in holdings:
            latest_price_rec = self.db.query(Price).filter(Price.ticker == h.ticker).order_by(Price.date.desc()).first()
            if not latest_price_rec:
                continue
                
            current_price = latest_price_rec.close
            currency = self.currency_service.get_currency_for_country(h.country)
            
            # Value in native currency
            value_native = current_price * h.quantity
            
            # Value in USD for consolidated metrics
            if currency == "INR":
                value_usd = self.currency_service.convert_inr_to_usd(value_native)
            else:
                value_usd = value_native
                
            total_value_usd += value_usd
            
            # Fetch sector info
            try:
                info = yf.Ticker(h.ticker).info
                sector = info.get('sector', 'Unknown')
            except:
                sector = 'Unknown'

            portfolio_data.append({
                "ticker": h.ticker,
                "quantity": h.quantity,
                "price": current_price,
                "value_native": round(value_native, 2),
                "value_usd": value_usd,
                "currency": currency,
                "sector": sector
            })

        if total_value_usd == 0:
            return {"error": "Portfolio value is zero."}

        # 2. Allocation & Sector Exposure
        df = pd.DataFrame(portfolio_data)
        df['allocation'] = (df['value_usd'] / total_value_usd) * 100
        
        max_allocation = df['allocation'].max()
        max_alloc_ticker = df.loc[df['allocation'].idxmax(), 'ticker']
        
        sector_exposure = df.groupby('sector')['allocation'].sum().to_dict()
        
        # 3. Correlation Matrix (last 1 year)
        price_data = {}
        for ticker in tickers:
            prices = self.db.query(Price.date, Price.close).filter(Price.ticker == ticker).order_by(Price.date.asc()).all()
            if prices:
                price_data[ticker] = pd.Series({p.date: p.close for p in prices})
        
        corr_matrix = {}
        if len(price_data) > 1:
            price_df = pd.DataFrame(price_data).ffill().dropna()
            if not price_df.empty:
                corr = price_df.pct_change().corr().replace({np.nan: 0})
                corr_matrix = corr.to_dict()

        # 4. Drawdown Monitoring
        drawdowns = {}
        for ticker in tickers:
            prices = self.db.query(Price.close).filter(Price.ticker == ticker).order_by(Price.date.asc()).all()
            if prices:
                close_prices = [p.close for p in prices]
                rolling_max = pd.Series(close_prices).expanding().max()
                current_drawdown = ((close_prices[-1] - rolling_max.iloc[-1]) / rolling_max.iloc[-1]) * 100
                drawdowns[ticker] = round(float(current_drawdown), 2)

        # Exchange rate for display
        usd_inr_rate = self.currency_service.get_latest_rate()

        return {
            "total_value_usd": round(float(total_value_usd), 2),
            "total_value_inr": round(float(self.currency_service.convert_usd_to_inr(total_value_usd)), 2),
            "exchange_rate": float(usd_inr_rate),
            "holdings": df.drop(columns=['value_usd']).to_dict(orient='records'),
            "max_allocation": {
                "ticker": max_alloc_ticker,
                "percentage": round(float(max_allocation), 2),
                "warning": bool(max_allocation > 20)
            },
            "sector_exposure": {s: round(float(v), 2) for s, v in sector_exposure.items()},
            "sector_warnings": [str(s) for s, v in sector_exposure.items() if v > 40],
            "correlation_matrix": corr_matrix,
            "asset_drawdowns": drawdowns,
            "drawdown_alerts": [str(t) for t, d in drawdowns.items() if d < -15]
        }
