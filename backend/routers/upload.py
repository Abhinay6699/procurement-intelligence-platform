from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_upload_status():
    return {"status": "Upload module pending Phase 3 integration"}
