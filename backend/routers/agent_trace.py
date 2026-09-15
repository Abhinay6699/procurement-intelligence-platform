from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_agent_trace():
    return {"status": "Agent trace pending Phase 4 LangGraph integration"}
