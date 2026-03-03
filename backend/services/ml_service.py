import os
import joblib
import pandas as pd
import numpy as np
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score
from lightgbm import LGBMClassifier
import shap
from models import Feature, Prediction

MODEL_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")

class MLService:
    def __init__(self, db: Session):
        self.db = db
        if not os.path.exists(MODEL_ROOT):
            os.makedirs(MODEL_ROOT)
        
        # Ensure country subdirs exist
        for country in ['us', 'ind']:
            os.makedirs(os.path.join(MODEL_ROOT, country), exist_ok=True)
            os.makedirs(os.path.join(MODEL_ROOT, country, "latest"), exist_ok=True)

    def _get_country_from_ticker(self, ticker: str) -> str:
        return "ind" if ticker.upper().endswith(".NS") else "us"

    def predict(self, ticker: str):
        ticker = ticker.upper()
        country = self._get_country_from_ticker(ticker)
        latest_dir = os.path.join(MODEL_ROOT, country, "latest")
        model_path = os.path.join(latest_dir, "lgbm_model.joblib")
        feature_list_path = os.path.join(latest_dir, "feature_list.json")
        metadata_path = os.path.join(latest_dir, "model_metadata.json")

        if not os.path.exists(model_path) or not os.path.exists(feature_list_path):
            return {"error": f"Model for {country} not found. Please train the {country} model first."}
        
        # Load metadata for version info
        version = "unknown"
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                version = metadata.get("version", "unknown")

        # 1. Load model and features
        model = joblib.load(model_path)
        with open(feature_list_path, 'r') as f:
            features = json.load(f)

        # 2. Get latest features for ticker
        query = select(Feature).where(Feature.ticker == ticker).order_by(Feature.date.desc()).limit(1)
        latest_feature = self.db.execute(query).scalar_one_or_none()

        if not latest_feature:
            return {"error": f"No features found for {ticker}. Please generate features first."}

        # 3. Prepare data
        data = {}
        for feat in features:
            data[feat] = getattr(latest_feature, feat)
        
        df = pd.DataFrame([data])
        
        # Check for NaNs
        if df.isnull().values.any():
            return {"error": f"Incomplete feature data for {ticker}. Prediction aborted."}

        # 4. Predict
        probs = model.predict_proba(df[features])[0]
        prob_positive = float(probs[1])

        # 5. Map to score and recommendation
        score = round(prob_positive * 100, 2)
        if prob_positive > 0.6:
            recommendation = "Buy"
            confidence = prob_positive
        elif prob_positive < 0.4:
            recommendation = "Sell"
            confidence = 1.0 - prob_positive
        else:
            recommendation = "Hold"
            confidence = 1.0 - abs(prob_positive - 0.5) * 2 # Lower confidence near 0.5

        # 6. Save prediction to DB
        prediction_record = Prediction(
            ticker=ticker,
            score=score,
            recommendation=recommendation,
            confidence=confidence,
            probability=prob_positive,
            model_version=version
        )
        self.db.add(prediction_record)
        self.db.commit()
        self.db.refresh(prediction_record)

        return {
            "ticker": ticker,
            "score": score,
            "recommendation": recommendation,
            "confidence": confidence,
            "date": prediction_record.date.isoformat() if prediction_record.date else datetime.now().isoformat(),
            "model_version": version
        }

    def get_explanation(self, ticker: str):
        ticker = ticker.upper()
        country = self._get_country_from_ticker(ticker)
        latest_dir = os.path.join(MODEL_ROOT, country, "latest")
        model_path = os.path.join(latest_dir, "lgbm_model.joblib")
        feature_list_path = os.path.join(latest_dir, "feature_list.json")

        if not os.path.exists(model_path) or not os.path.exists(feature_list_path):
            return {"error": f"Model for {country} not found. Please train the {country} model first."}

        # 1. Load model and features
        model = joblib.load(model_path)
        with open(feature_list_path, 'r') as f:
            features = json.load(f)

        # 2. Get latest features for ticker
        query = select(Feature).where(Feature.ticker == ticker).order_by(Feature.date.desc()).limit(1)
        latest_feature = self.db.execute(query).scalar_one_or_none()

        if not latest_feature:
            return {"error": f"No features found for {ticker}. Please generate features first."}

        # 3. Prepare data
        data = {}
        for feat in features:
            data[feat] = getattr(latest_feature, feat)
        
        df = pd.DataFrame([data])
        
        # Check for NaNs
        if df.isnull().values.any():
            return {"error": f"Incomplete feature data for {ticker}. Explanation aborted."}

        # 4. SHAP Explanation
        # For LGBMClassifier, we use TreeExplainer
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(df[features])

        # shap_values is a list for multi-class or binary classification
        # For binary, it's [shap_values_for_class_0, shap_values_for_class_1]
        # We want the explanation for the positive class (class 1)
        if isinstance(shap_values, list):
            sv = shap_values[1][0]
        else:
            sv = shap_values[0]

        # 5. Extract top drivers
        indices = np.argsort(sv)
        
        # Top positive drivers (sorted desc)
        pos_indices = indices[sv[indices] > 0][::-1]
        top_positive = []
        for i in pos_indices:
            top_positive.append({
                "feature": features[i],
                "impact": float(sv[i]),
                "value": float(df[features[i]].iloc[0])
            })

        # Top negative drivers (sorted asc)
        neg_indices = indices[sv[indices] < 0]
        top_negative = []
        for i in neg_indices:
            top_negative.append({
                "feature": features[i],
                "impact": float(sv[i]),
                "value": float(df[features[i]].iloc[0])
            })

        return {
            "ticker": ticker,
            "top_positive": top_positive[:5],
            "top_negative": top_negative[:5],
            "base_value": float(explainer.expected_value[1] if isinstance(explainer.expected_value, (list, np.ndarray)) else explainer.expected_value)
        }

    def train_model(self, country: str = "US"):
        country = country.lower()
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        country_dir = os.path.join(MODEL_ROOT, country)
        model_dir = os.path.join(country_dir, version)
        latest_dir = os.path.join(country_dir, "latest")
        
        os.makedirs(model_dir, exist_ok=True)
        os.makedirs(latest_dir, exist_ok=True)

        model_path = os.path.join(model_dir, "lgbm_model.joblib")
        feature_list_path = os.path.join(model_dir, "feature_list.json")
        metadata_path = os.path.join(model_dir, "model_metadata.json")
        
        latest_model_path = os.path.join(latest_dir, "lgbm_model.joblib")
        latest_feature_list_path = os.path.join(latest_dir, "feature_list.json")
        latest_metadata_path = os.path.join(latest_dir, "model_metadata.json")
        
        # 1. Load data and filter by country
        query = select(Feature).where(Feature.target_class.isnot(None))
        if country == "ind":
            query = query.where(Feature.ticker.like("%.NS"))
        else:
            query = query.where(~Feature.ticker.like("%.NS"))
            
        result = self.db.execute(query).scalars().all()
        
        if not result:
            return {"error": f"No data with targets found for {country} training. Please generate features first."}

        # Convert to DataFrame
        data = []
        for f in result:
            d = {
                'ticker': f.ticker,
                'date': f.date,
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
            }
            data.append(d)

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Define features and target
        target = 'target_class'
        features = [
            'rsi', 'macd', 'macd_signal', 'dma_50', 'dma_200', 
            'momentum_1m', 'momentum_3m', 'momentum_6m', 
            'volatility_30d', 'drawdown', 'relative_strength', 
            'rolling_outperformance', 'beta'
        ]
        
        # Drop rows with NaN in features or target
        df = df.dropna(subset=features + [target])

        if len(df) < 50:
            return {"error": f"Insufficient data for training: {len(df)} valid rows. Need more historical data or features."}

        X = df[features]
        y = df[target]

        # 2. TimeSeriesSplit Validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        aucs = []
        for train_index, test_index in tscv.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            
            # Use simple params for initial model
            model = LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                num_leaves=31,
                random_state=42,
                verbose=-1
            )
            model.fit(X_train, y_train)
            
            y_prob = model.predict_proba(X_test)[:, 1]
            try:
                auc = roc_auc_score(y_test, y_prob)
                aucs.append(auc)
            except ValueError:
                # Handle cases where only one class is present in test set
                continue

        mean_auc = np.mean(aucs) if aucs else 0.0
        # Ensure mean_auc is JSON compliant
        if np.isnan(mean_auc) or np.isinf(mean_auc):
            mean_auc = 0.0

        # 3. Final train on all data
        final_model = LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            verbose=-1
        )
        final_model.fit(X, y)

        # 4. Save model
        joblib.dump(final_model, model_path)
        joblib.dump(final_model, latest_model_path)
        
        # 5. Save feature list
        with open(feature_list_path, 'w') as f:
            json.dump(features, f)
        with open(latest_feature_list_path, 'w') as f:
            json.dump(features, f)

        # 6. Save metadata
        # Helper to make values JSON compliant
        def clean_val(v):
            if isinstance(v, (float, np.float32, np.float64)):
                if np.isnan(v) or np.isinf(v):
                    return 0.0
            return float(v)

        metadata = {
            "version": version,
            "country": country,
            "trained_at": datetime.now().isoformat(),
            "mean_auc": clean_val(mean_auc),
            "samples": len(df),
            "features": features,
            "val_scores": [clean_val(a) for a in aucs]
        }
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
        with open(latest_metadata_path, 'w') as f:
            json.dump(metadata, f)

        print(f"Model trained and saved to {model_dir} and {latest_dir}")
        return metadata
