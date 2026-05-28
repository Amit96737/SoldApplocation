import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DB_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE URL not found in .env file")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # Ensure stale connections aren't used
    pool_recycle=1800,  # Recycle every 30 mins to avoid idle disconnects
    pool_size=10,  # Number of connections in the pool
    max_overflow=20,  # Extra connections allowed (burst traffic)
    pool_timeout=30
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

Base.metadata.create_all(bind=engine)


