from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_reports_status():
    return {"status": "Reports module pending Phase 6"}
