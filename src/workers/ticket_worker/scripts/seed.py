import os
import pandas as pd
from celery import Celery
from sqlalchemy import create_engine, Text, String, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB


def seed_database(batch_size=1000):
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASS = os.getenv("POSTGRES_PASSWORD", "postgres")
    DB_HOST = os.getenv("POSTGRES_HOST", "database")
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "tickets_db")

    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(DATABASE_URL)

    df = pd.read_csv("hf://datasets/Tobi-Bueck/customer-support-tickets/dataset-tickets-multi-lang-4-20k.csv")

    tag_cols = [f"tag_{i}" for i in range(1, 9)]
    df["tags"] = df.apply(lambda row: {col: row[col] for col in tag_cols if pd.notnull(row[col])}, axis=1)
    df["predicted_category"] = None
    df["ground_truth_category"] = None
    df["confidence"] = None
    df["summary"] = None
    df["processed_at"] = None

    columns = [
        "subject", "body", "answer", "type", "queue", "priority", "language", "tags",
        "predicted_category", "confidence", "summary", "processed_at", "ground_truth_category"
    ]
    df = df[columns]

    for start in range(0, len(df), batch_size):
        end = start + batch_size
        chunk = df[start:end]
        chunk.to_sql(
            "customer_support_tickets",
            con=engine,
            if_exists="append",
            index=False,
            dtype={
                "subject": Text,
                "body": Text,
                "answer": Text,
                "type": String(50),
                "queue": String(50),
                "priority": String(20),
                "language": String(10),
                "tags": JSONB,
                "predicted_category": String(50),
                "confidence": Float,
                "summary": Text,
                "processed_at": DateTime,
                "ground_truth_category": String(50),
            }
        )
        print(f"✅ Subido batch: {start} - {end}")
