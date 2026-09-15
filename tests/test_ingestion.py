import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.models import Vendor
from backend.ingestion import ingest_data

SQLALCHEMY_DATABASE_URL = "sqlite:///./data/test_procurement.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_ingestion(db, monkeypatch):
    monkeypatch.setattr("backend.ingestion.SessionLocal", TestingSessionLocal)
    
    ingest_data()
    
    vendors = db.query(Vendor).all()
    assert len(vendors) > 0, "No vendors were ingested"
