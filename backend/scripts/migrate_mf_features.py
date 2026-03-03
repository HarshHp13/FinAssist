from sqlalchemy import create_session, create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/finassist")
engine = create_engine(DATABASE_URL)

def migrate():
    with engine.connect() as conn:
        print("Adding MF columns to features table...")
        
        columns = [
            ("cagr_1y", "FLOAT"),
            ("cagr_3y", "FLOAT"),
            ("cagr_5y", "FLOAT"),
            ("alpha", "FLOAT"),
            ("sharpe", "FLOAT"),
            ("rolling_consistency", "FLOAT"),
            ("expense_ratio", "FLOAT")
        ]
        
        for col_name, col_type in columns:
            try:
                conn.execute(text(f"ALTER TABLE features ADD COLUMN {col_name} {col_type};"))
                print(f"Added column {col_name}")
            except Exception as e:
                print(f"Column {col_name} might already exist or error: {e}")
        
        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
