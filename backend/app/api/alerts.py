from fastapi import APIRouter

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.post("/notify")
def notify_alert(user_id: str, message: str):
    # TODO: integrate with real notification service (email/SMS/push)
    return {"status": "queued", "user_id": user_id, "message": message}