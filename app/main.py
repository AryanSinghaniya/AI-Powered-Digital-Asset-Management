from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as api_router
import os
from app.core.config import settings
from app.db.database import engine, Base

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Local DAM API")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app.include_router(api_router, prefix="/api")

# Ensure ui directory exists
os.makedirs(os.path.join(os.path.dirname(__file__), 'ui'), exist_ok=True)

app.mount("/ui", StaticFiles(directory=os.path.join(os.path.dirname(__file__), 'ui')), name="ui")

@app.get("/")
def read_root():
    return RedirectResponse(url="/ui/index.html")

@app.get("/health")
def health_check():
    return {"status": "ok"}
