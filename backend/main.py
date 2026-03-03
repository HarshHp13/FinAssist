import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List

from models import Base, Holding as HoldingModel, Price as PriceModel, MacroData as MacroDataModel, Feature as FeatureModel
import schemas
from services.data_fetcher import DataFetcher
from services.feature_engineer import FeatureEngineer
from services.ml_service import MLService
from services.risk_service import RiskService

app = FastAPI()

origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/finassist")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "FinAssist Backend API"}

@app.get("/health/db")
def check_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/holdings/", response_model=schemas.Holding)
def create_holding(holding: schemas.HoldingCreate, db: Session = Depends(get_db)):
    db_holding = HoldingModel(**holding.model_dump())
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    fetcher = DataFetcher(db)
    fetcher.sync_portfolio()
    return db_holding

@app.get("/holdings/", response_model=List[schemas.Holding])
def read_holdings(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    holdings = db.query(HoldingModel).offset(skip).limit(limit).all()
    return holdings

@app.get("/holdings/{holding_id}", response_model=schemas.Holding)
def read_holding(holding_id: int, db: Session = Depends(get_db)):
    db_holding = db.query(HoldingModel).filter(HoldingModel.id == holding_id).first()
    if db_holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    return db_holding

@app.delete("/holdings/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    db_holding = db.query(HoldingModel).filter(HoldingModel.id == holding_id).first()
    if db_holding is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(db_holding)
    db.commit()
    return {"message": "Holding deleted successfully"}

@app.get("/predict/{ticker}", response_model=schemas.Prediction)
def get_prediction(ticker: str, db: Session = Depends(get_db)):
    ml_service = MLService(db)
    result = ml_service.predict(ticker)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/explain/{ticker}")
def get_explanation(ticker: str, db: Session = Depends(get_db)):
    ml_service = MLService(db)
    result = ml_service.get_explanation(ticker)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/sync/history/{ticker}")
def sync_ticker_history(ticker: str, db: Session = Depends(get_db)):
    fetcher = DataFetcher(db)
    # Check if it's a Mutual Fund in holdings to decide fetcher method
    holding = db.query(HoldingModel).filter(HoldingModel.ticker == ticker).first()
    
    if holding and holding.asset_type == 'MF' and holding.country == 'IND':
        success = fetcher.fetch_mf_nav(ticker)
    else:
        success = fetcher.fetch_historical_data(ticker.upper())
        
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data for {ticker}")
    return {"message": f"Successfully synced {ticker}"}

@app.post("/sync/portfolio")
def sync_portfolio_history(db: Session = Depends(get_db)):
    fetcher = DataFetcher(db)
    fetcher.sync_portfolio()
    return {"message": "Portfolio history sync initiated"}

@app.get("/prices/{ticker}", response_model=List[schemas.Price])
def get_prices(ticker: str, db: Session = Depends(get_db)):
    prices = db.query(PriceModel).filter(PriceModel.ticker == ticker.upper()).order_by(PriceModel.date.desc()).all()
    return prices

@app.post("/sync/indices")
def sync_indices(db: Session = Depends(get_db)):
    fetcher = DataFetcher(db)
    fetcher.sync_indices()
    return {"message": "Indices and macro indicators sync initiated"}

@app.get("/macro/{symbol}", response_model=List[schemas.MacroData])
def get_macro_data(symbol: str, db: Session = Depends(get_db)):
    # Symbols like ^GSPC, ^NSEI, ^VIX, ^TNX
    # Need to handle URI encoding for '^' if passed in URL
    data = db.query(MacroDataModel).filter(MacroDataModel.symbol == symbol).order_by(MacroDataModel.date.desc()).all()
    return data

@app.get("/validate/{ticker}")
def validate_ticker_data(ticker: str, db: Session = Depends(get_db)):
    fetcher = DataFetcher(db)
    return fetcher.validate_data_integrity(ticker.upper())

@app.post("/features/generate/{ticker}")
def generate_features(ticker: str, db: Session = Depends(get_db)):
    engineer = FeatureEngineer(db)
    success = engineer.generate_features(ticker.upper())
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to generate features for {ticker}")
    return {"message": f"Successfully generated features for {ticker}"}

@app.get("/features/{ticker}", response_model=List[schemas.Feature])
def get_features(ticker: str, db: Session = Depends(get_db)):
    features = db.query(FeatureModel).filter(FeatureModel.ticker == ticker.upper()).order_by(FeatureModel.date.desc()).all()
    return features

@app.post("/model/train")
def train_model(country: str = "US", db: Session = Depends(get_db)):
    ml_service = MLService(db)
    result = ml_service.train_model(country=country)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/backtest/run")
def run_backtest(start_date: str = "2022-01-01", top_n: int = 5, db: Session = Depends(get_db)):
    from services.backtest_service import BacktestService
    service = BacktestService(db)
    result = service.run_walk_forward_backtest(start_date_str=start_date, top_n=top_n)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/risk/metrics")
def get_risk_metrics(db: Session = Depends(get_db)):
    service = RiskService(db)
    result = service.get_portfolio_risk_metrics()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
