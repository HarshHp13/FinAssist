import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Change this if running outside Docker
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/finassist")

def migrate():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        print("Adding country column to holdings table...")
        try:
            connection.execute(text("ALTER TABLE holdings ADD COLUMN country VARCHAR DEFAULT 'US';"))
            connection.commit()
            print("Successfully added country column.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Column country already exists.")
            else:
                print(f"Error adding country column: {e}")

        print("Adding benchmark_symbol column to holdings table...")
        try:
            connection.execute(text("ALTER TABLE holdings ADD COLUMN benchmark_symbol VARCHAR DEFAULT '^GSPC';"))
            connection.commit()
            print("Successfully added benchmark_symbol column.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Column benchmark_symbol already exists.")
            else:
                print(f"Error adding benchmark_symbol column: {e}")

if __name__ == "__main__":
    migrate()
