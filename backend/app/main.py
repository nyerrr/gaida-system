from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.intent_router import analyze_intent
from app.services.virtual_agent import generate_response
from app.api import auth
from app.api.voice import router as audio_router

app = FastAPI(title="GAIDA Backend")

# Include API routers
app.include_router(auth.router)
app.include_router(audio_router)

# Enable CORS for local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# accept optional session_id
class UserInput(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/")
def root():
    return {"status": "ok", "message": "GAIDA Backend"}


@app.post("/virtual-agent")
def virtual_agent(input: UserInput):
    intent_data = analyze_intent(
        user_message=input.message,
        session_id=input.session_id
    )

    response_text = (
        intent_data.get("response")
        if isinstance(intent_data, dict) and intent_data.get("response")
        else generate_response(intent_data)
    )

    return {
        "session_id": intent_data.get("session_id"),
        "intent": intent_data.get("intent"),
        "confidence": intent_data.get("confidence"),
        "response": response_text,
        "method": intent_data.get("method")
    }