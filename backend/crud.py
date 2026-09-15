from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

def get_vendor(db: Session, vendor_id: int):
    return db.query(models.Vendor).filter(models.Vendor.id == vendor_id).first()

def get_vendors(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Vendor).offset(skip).limit(limit).all()

def get_dashboard_stats(db: Session):
    total_invoices = db.query(models.Invoice).count()
    total_vendors = db.query(models.Vendor).count()
    flagged_invoices = db.query(models.Recommendation).filter(models.Recommendation.ml_flag != "None").count()
    
    risk_dist = {
        "High": db.query(models.Vendor).filter(models.Vendor.risk_tier == "High").count(),
        "Medium": db.query(models.Vendor).filter(models.Vendor.risk_tier == "Medium").count(),
        "Low": db.query(models.Vendor).filter(models.Vendor.risk_tier == "Low").count()
    }
    
    return {
        "total_invoices": total_invoices,
        "total_vendors": total_vendors,
        "flagged_invoices": flagged_invoices,
        "risk_distribution": risk_dist
    }
