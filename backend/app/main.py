# backend/app/main.py
import sys
import os

# ----------------------------
# Add project root to Python path
# ----------------------------
# This allows importing frontend modules when running backend alone
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# ----------------------------
# Imports
# ----------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Internal backend services
from app.services.intent_router import analyze_intent
from app.services.virtual_agent import generate_response
from app.api import auth

# Frontend module
from frontend.src.voice import router as audio_router

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="GAIDA Backend")

# Include API routers
app.include_router(auth.router)
app.include_router(audio_router)

# Enable CORS for local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # you can restrict to frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Pydantic model
# ----------------------------
class UserInput(BaseModel):
    message: str
    session_id: str | None = None

# ----------------------------
# Routes
# ----------------------------
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