from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, crud
from ..database import get_db
from .auth import get_current_user

router = APIRouter()

@router.get("/stats")
def read_dashboard_stats(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return crud.get_dashboard_stats(db)
