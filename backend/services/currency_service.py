import logging
import pandas as pd
from sqlalchemy.orm import Session
from models import MacroData
from datetime import datetime

logger = logging.getLogger(__name__)

class CurrencyService:
    def __init__(self, db: Session):
        self.db = db
        self.conversion_symbol = "USDINR=X"

    def get_latest_rate(self) -> float:
        """
        Get the latest USD to INR exchange rate.
        Defaults to 83.0 if no data is found after a warning.
        """
        rate_rec = self.db.query(MacroData).filter(
            MacroData.symbol == self.conversion_symbol
        ).order_by(MacroData.date.desc()).first()

        if rate_rec:
            return rate_rec.value
        
        logger.warning(f"No exchange rate data found for {self.conversion_symbol}. Using default 83.0")
        return 83.0

    def convert_usd_to_inr(self, amount_usd: float) -> float:
        rate = self.get_latest_rate()
        return amount_usd * rate

    def convert_inr_to_usd(self, amount_inr: float) -> float:
        rate = self.get_latest_rate()
        if rate == 0:
            return 0.0
        return amount_inr / rate

    def get_currency_for_country(self, country: str) -> str:
        country = country.upper()
        if country == "IND":
            return "INR"
        return "USD"

    def get_rate_at_date(self, date: datetime) -> float:
        """
        Find the exchange rate closest to the given date without going into the future.
        """
        rate_rec = self.db.query(MacroData).filter(
            MacroData.symbol == self.conversion_symbol,
            MacroData.date <= date
        ).order_by(MacroData.date.desc()).first()

        if rate_rec:
            return rate_rec.value
        
        # Fallback to absolute latest if date is behind all records or check first record
        first_rec = self.db.query(MacroData).filter(
            MacroData.symbol == self.conversion_symbol
        ).order_by(MacroData.date.asc()).first()

        if first_rec:
            return first_rec.value

        return 83.0
