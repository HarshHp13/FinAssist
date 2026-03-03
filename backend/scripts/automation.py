import os
import sys
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Add the parent directory to sys.path to allow importing from 'backend'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Holding
from services.data_fetcher import DataFetcher
from services.ml_service import MLService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AutomationJob")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/finassist")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def weekly_prediction_job():
    """
    PR 6.1: Weekly Prediction Cron
    - Data refresh job
    - Feature recompute
    - Inference run
    - Logging
    """
    logger.info("Starting Weekly Prediction Job...")
    db = SessionLocal()
    try:
        fetcher = DataFetcher(db)
        ml_service = MLService(db)
        
        # 1. Sync Indices (Macro data)
        logger.info("Step 1: Syncing Indices (Macro Indicators)...")
        fetcher.sync_indices()
        
        # 2. Sync Portfolio Holdings and Recompute Features
        logger.info("Step 2: Syncing Portfolio Data and Recomputing Features...")
        fetcher.sync_portfolio()
        
        # 3. Run Inference for all tickers in portfolio
        logger.info("Step 3: Running Inference for portfolio assets...")
        holdings = db.query(Holding.ticker).distinct().all()
        tickers = [h.ticker for h in holdings]
        
        if not tickers:
            logger.warning("No tickers found in portfolio to predict.")
        
        for ticker in tickers:
            logger.info(f"Generating prediction for {ticker}...")
            result = ml_service.predict(ticker)
            if "error" in result:
                logger.error(f"Prediction failed for {ticker}: {result['error']}")
            else:
                logger.info(f"Prediction successful for {ticker}: {result['recommendation']} (Score: {result['score']})")
                
        logger.info("Weekly Prediction Job completed successfully.")
        
    except Exception as e:
        logger.error(f"Weekly Prediction Job failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

def monthly_retraining_job():
    """
    PR 6.2: Monthly Retraining Cron
    - Retrain model
    - Version increment
    - Store training metrics
    """
    logger.info("Starting Monthly Retraining Job...")
    db = SessionLocal()
    try:
        ml_service = MLService(db)
        
        # Retrain model
        logger.info("Retraining model with latest historical features...")
        result = ml_service.train_model()
        
        if "error" in result:
            logger.error(f"Retraining failed: {result['error']}")
        else:
            logger.info(f"Retraining successful.")
            logger.info(f"New Version: {result.get('version')}")
            logger.info(f"Mean AUC Score: {result.get('mean_auc')}")
            logger.info(f"Training Samples: {result.get('samples')}")
            
        logger.info("Monthly Retraining Job completed.")
        
    except Exception as e:
        logger.error(f"Monthly Retraining Job failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_type = sys.argv[1]
        if job_type == "weekly":
            weekly_prediction_job()
        elif job_type == "monthly":
            monthly_retraining_job()
        else:
            logger.error(f"Unknown job type: {job_type}. Use 'weekly' or 'monthly'.")
    else:
        # Default to weekly if no arg
        weekly_prediction_job()
