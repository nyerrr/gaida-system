from fastapi import FastAPI
from app.api import text, classify

app = FastAPI(title="GAIDA Backend")

app.include_router(text.router)
app.include_router(classify.router)

@app.get("/")
def root():
    return {"status": "GAIDA backend running"}
