from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/counselor", tags=["counselor"])

class CounselorRequest(BaseModel):
    user_id: str
    message: str

@router.post("/recommend")
def recommend_counselor(payload: CounselorRequest):
    # placeholder recommendation logic
    return {"recommended": "Dr. Reyes", "confidence": 0.75}