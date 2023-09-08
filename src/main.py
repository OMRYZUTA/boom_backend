from fastapi import FastAPI
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

@app.get("/api/meeting/generate")
def read_root():
    return {"time": "tomorrow"}
