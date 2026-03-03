from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HoldingBase(BaseModel):
    ticker: str
    quantity: float
    average_price: float
    country: str = "US"
    benchmark_symbol: str = "^GSPC"
    asset_type: str = "STOCK"

class HoldingCreate(HoldingBase):
    pass

class HoldingUpdate(BaseModel):
    ticker: Optional[str] = None
    quantity: Optional[float] = None
    average_price: Optional[float] = None
    country: Optional[str] = None
    benchmark_symbol: Optional[str] = None
    asset_type: Optional[str] = None

class Holding(HoldingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Prediction(BaseModel):
    ticker: str
    score: float
    recommendation: str
    confidence: float
    date: Optional[str] = None
    model_version: Optional[str] = None

class PriceBase(BaseModel):
    ticker: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class Price(PriceBase):
    id: int

    class Config:
        from_attributes = True

class MacroDataBase(BaseModel):
    symbol: str
    date: datetime
    value: float

class MacroData(MacroDataBase):
    id: int

    class Config:
        from_attributes = True

class FeatureBase(BaseModel):
    ticker: str
    date: datetime
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    dma_50: Optional[float] = None
    dma_200: Optional[float] = None
    momentum_1m: Optional[float] = None
    momentum_3m: Optional[float] = None
    momentum_6m: Optional[float] = None
    volatility_30d: Optional[float] = None
    drawdown: Optional[float] = None
    relative_strength: Optional[float] = None
    rolling_outperformance: Optional[float] = None
    beta: Optional[float] = None
    target_return_90d: Optional[float] = None
    target_class: Optional[int] = None

class Feature(FeatureBase):
    id: int

    class Config:
        from_attributes = True

class BenchmarkMappingBase(BaseModel):
    asset_type: str
    country: str
    benchmark_symbol: str

class BenchmarkMapping(BenchmarkMappingBase):
    id: int

    class Config:
        from_attributes = True
