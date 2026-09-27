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

@app.on_event("startup")
def startup_event():
    import threading
    import logging
    from app.db.database import SessionLocal
    from app.db.models import FileRecord
    from app.api.endpoints import run_indexing_pipeline
    
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        count = db.query(FileRecord).count()
    except Exception as e:
        logger.error(f"Failed to query FileRecord: {e}")
        count = 0
    finally:
        db.close()
        
    sample_dir = "/app/sample_media"
    # Also fallback to local test dir if running locally
    if not os.path.exists(sample_dir):
        sample_dir = "./sample_media"
        
    if count == 0 and os.path.exists(sample_dir):
        logger.info(f"Database is empty. Auto-indexing {sample_dir}...")
        thread = threading.Thread(target=run_indexing_pipeline, args=(sample_dir,))
        thread.start()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
