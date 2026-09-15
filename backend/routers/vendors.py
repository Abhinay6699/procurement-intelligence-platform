from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, crud
from ..database import get_db
from .auth import get_current_user

router = APIRouter()

@router.get("/", response_model=list[schemas.Vendor])
def read_vendors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    vendors = crud.get_vendors(db, skip=skip, limit=limit)
    return vendors

@router.get("/{vendor_id}", response_model=schemas.Vendor)
def read_vendor(vendor_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_vendor = crud.get_vendor(db, vendor_id=vendor_id)
    if db_vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return db_vendor
