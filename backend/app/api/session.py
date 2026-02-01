from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/session", tags=["session"])

class SessionCreate(BaseModel):
    user_id: str

@router.post("/start")
def start_session(payload: SessionCreate):
    # TODO: persist the session in DB
    return {"session_id": f"{payload.user_id}-session-1"}