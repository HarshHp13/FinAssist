from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    country = Column(String, default='US')
    benchmark_symbol = Column(String, default='^GSPC')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Price(Base):
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # Ensure no duplicate ticker/date entries
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uix_ticker_date'),
    )

class MacroData(Base):
    __tablename__ = "macro_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)  # ^GSPC, ^NSEI, ^VIX, ^TNX
    date = Column(DateTime(timezone=True), nullable=False)
    value = Column(Float, nullable=False)
    
    # Ensure no duplicate symbol/date entries
    __table_args__ = (
        UniqueConstraint('symbol', 'date', name='uix_symbol_date'),
    )

class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    
    # Technical Indicators (PR 3.1)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    dma_50 = Column(Float)
    dma_200 = Column(Float)
    momentum_1m = Column(Float)
    momentum_3m = Column(Float)
    momentum_6m = Column(Float)
    volatility_30d = Column(Float)
    drawdown = Column(Float)

    # Relative Strength (PR 3.2)
    relative_strength = Column(Float)  # Price / Index Price
    rolling_outperformance = Column(Float) # Stock Return - Index Return (90d)
    beta = Column(Float)

    # Target (PR 3.3)
    target_return_90d = Column(Float)
    target_class = Column(Integer)  # 1 if return > 0, else 0

    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uix_feature_ticker_date'),
    )

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Float)
    recommendation = Column(String)
    confidence = Column(Float)
    probability = Column(Float)
    model_version = Column(String)
