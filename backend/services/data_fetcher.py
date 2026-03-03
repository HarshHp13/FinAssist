import yfinance as yf
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from models import Price, Holding, MacroData
import logging
from services.feature_engineer import FeatureEngineer

# Enhanced Logging System
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self, db: Session):
        self.db = db

    def _normalize_date(self, dt):
        """
        Timestamp normalization: Ensure all dates are in UTC.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _normalize_ticker(self, ticker: str, country: str = "US"):
        """
        Normalize ticker based on country.
        E.g., TCS -> TCS.NS for India.
        """
        ticker = ticker.strip().upper()
        if country == "IND" and not ticker.endswith(".NS"):
            return f"{ticker}.NS"
        return ticker

    def fetch_historical_data(self, ticker: str, period: str = "5y", interval: str = "1d"):
        """
        Fetch historical OHLCV data for a ticker using yfinance.
        Includes missing data handling and normalization.
        """
        logger.info(f"Fetching historical data for {ticker}...")
        try:
            df = yf.download(ticker, period=period, interval=interval)
            
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                return False

            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Missing Data Handling: Drop rows with missing values
            initial_count = len(df)
            df = df.dropna()
            final_count = len(df)
            if initial_count > final_count:
                logger.info(f"Dropped {initial_count - final_count} rows with missing values for {ticker}")

            # Reset index to get full date info
            df = df.reset_index()
            
            new_records = 0
            for index, row in df.iterrows():
                date_val = self._normalize_date(row['Date'].to_pydatetime())
                
                # No duplicate rows: Check for existing record
                existing = self.db.query(Price).filter(
                    Price.ticker == ticker,
                    Price.date == date_val
                ).first()
                
                if existing:
                    continue

                new_price = Price(
                    ticker=ticker,
                    date=date_val,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                )
                self.db.add(new_price)
                new_records += 1
            
            self.db.commit()
            logger.info(f"Successfully stored {new_records} new records for {ticker}")
            return True
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            self.db.rollback()
            return False

    def sync_portfolio(self):
        """
        Sync historical data for all tickers in the portfolio.
        Handles normalization for Indian stocks.
        """
        holdings = self.db.query(Holding.ticker, Holding.country).distinct().all()
        featuresGen = FeatureEngineer(self.db)
        
        for h in holdings:
            normalized_ticker = self._normalize_ticker(h.ticker, h.country)
            # Update the ticker in database if it was not normalized
            if normalized_ticker != h.ticker:
                logger.info(f"Normalizing ticker {h.ticker} to {normalized_ticker}")
                # Update all holdings with this ticker and country
                self.db.query(Holding).filter(
                    Holding.ticker == h.ticker, 
                    Holding.country == h.country
                ).update({"ticker": normalized_ticker})
                self.db.commit()
            
            self.fetch_historical_data(normalized_ticker)
            featuresGen.generate_features(normalized_ticker)

    def fetch_macro_data(self, symbol: str, period: str = "5y"):
        """
        Fetch historical data for indices or macro indicators.
        """
        logger.info(f"Fetching macro data for {symbol}...")
        try:
            df = yf.download(symbol, period=period, interval="1d")
            
            if df.empty:
                logger.warning(f"No data found for {symbol}")
                return False

            # Flatten MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Missing Data Handling
            df = df.dropna()

            df = df.reset_index()
            
            new_records = 0
            for index, row in df.iterrows():
                date_val = self._normalize_date(row['Date'].to_pydatetime())
                
                existing = self.db.query(MacroData).filter(
                    MacroData.symbol == symbol,
                    MacroData.date == date_val
                ).first()
                
                if existing:
                    continue

                # Use adjusted close or close as the value
                value = float(row['Close'])
                
                new_macro = MacroData(
                    symbol=symbol,
                    date=date_val,
                    value=value
                )
                self.db.add(new_macro)
                new_records += 1
            
            self.db.commit()
            logger.info(f"Successfully stored {new_records} new macro records for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error fetching macro data for {symbol}: {e}")
            self.db.rollback()
            return False

    def sync_indices(self):
        """
        Sync major indices and macro indicators.
        """
        # Added India-specific markers: ^INDIAVIX (Volatility) and USDINR=X (Currency)
        symbols = ["^GSPC", "^NSEI", "^VIX", "^TNX", "^INDIAVIX", "USDINR=X"]
        for symbol in symbols:
            self.fetch_macro_data(symbol)

    def validate_data_integrity(self, ticker: str):
        """
        PR 2.3: Data Integrity Validation
        Check for missing dates or anomalous values.
        """
        prices = self.db.query(Price).filter(Price.ticker == ticker).order_by(Price.date.asc()).all()
        if not prices:
            return {"status": "error", "message": "No data found"}
        
        # Check for gaps (simplified)
        gaps = []
        for i in range(1, len(prices)):
            diff = prices[i].date - prices[i-1].date
            if diff.days > 4: # Weekend (2) + 2 extra days tolerance
                gaps.append(f"Gap between {prices[i-1].date.date()} and {prices[i].date.date()}")
        
        return {
            "ticker": ticker,
            "count": len(prices),
            "gaps": gaps,
            "start_date": prices[0].date,
            "end_date": prices[-1].date
        }

