import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import Base

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    engine = create_engine(DATABASE_URL) if DATABASE_URL else None
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception:
    engine = None
    SessionLocal = None

def init_db():
    if engine:
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            pass

def get_db():
    if not SessionLocal:
        yield None
        return
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    if not engine:
        return False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except SQLAlchemyError:
        return False
