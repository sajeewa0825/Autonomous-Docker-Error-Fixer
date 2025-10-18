from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.loadenv import Settings

engine = create_engine(Settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)