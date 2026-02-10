from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.intent_router import analyze_intent
from app.services.virtual_agent import generate_response
from app.api import auth

app = FastAPI(title="GAIDA Backend")

# Include API routers
app.include_router(auth.router)

# Enable CORS for local frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserInput(BaseModel):
    message: str


@app.get("/")
def root():
    return {"status": "ok", "message": "GAIDA Backend"}


@app.post("/virtual-agent")
def virtual_agent(input: UserInput):
    intent_data = analyze_intent(input.message)
    response_text = generate_response(intent_data)

    return {
        "intent": intent_data.get("intent"),
        "confidence": intent_data.get("confidence"),
        "response": response_text,
    }
