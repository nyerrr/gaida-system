from fastapi import FastAPI
app = FastAPI(title="GAIDA Backend")

@app.get("/")
def root ():
    return {"status": "Backend is running"}