import os
import sys
import subprocess
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import FileRecord
from app.db.vector_store import get_collection
from app.services.embedding import embedding_service
from app.services.scanner import scan_directory
from app.services.indexer import process_pending_images, process_pending_videos, process_pending_pdfs

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Schemas ---

class SearchRequest(BaseModel):
    query: str
    file_types: Optional[List[str]] = None
    limit: int = 12

class SearchResult(BaseModel):
    filepath: str
    filename: str
    type: str
    score: float
    parent_id: Optional[int] = None
    size_bytes: Optional[int] = None
    formatted_size: Optional[str] = None

class IndexRequest(BaseModel):
    folder_path: str

class OpenRequest(BaseModel):
    filepath: str

# --- Endpoints ---

def run_indexing_pipeline(folder_path: str):
    db = next(get_db())
    try:
        # Robustness: Reset any records stuck in PROCESSING state due to abrupt termination
        stuck_records = db.query(FileRecord).filter(FileRecord.status == "PROCESSING").all()
        if stuck_records:
            for r in stuck_records:
                r.status = "PENDING"
                logger.info(f"Resetting stuck record {r.filename} to PENDING")
            db.commit()

        scan_directory(db, folder_path)
        process_pending_images(db)
        process_pending_videos(db)
        process_pending_pdfs(db)
    except Exception as e:
        logger.error(f"Indexing pipeline failed: {e}")
    finally:
        db.close()

@router.post("/index")
def start_indexing(request: IndexRequest, background_tasks: BackgroundTasks):
    from app.core.config import settings
    
    # Clean the path: strip whitespace and surrounding quotes (single or double)
    target_folder = request.folder_path.strip().strip('"').strip("'")
    
    # --- WINDOWS TO DOCKER TRANSLATION ---
    # Automatically convert C:\Users\... to /app/Users/... for Docker
    if "\\" in target_folder or target_folder.lower().startswith("c:"):
        target_folder = target_folder.replace("\\", "/")
        if target_folder.lower().startswith("c:/users/"):
            target_folder = "/app/" + target_folder[3:]
    # -------------------------------------
    
    if settings.demo_mode:
        target_folder = settings.scan_folder
        logger.info(f"DEMO MODE: Forcing scan folder to {target_folder}")
        
    resolved_path = os.path.abspath(target_folder)
    
    if not os.path.exists(resolved_path):
        logger.error(f"Indexing failed: Path does not exist -> {resolved_path}")
        raise HTTPException(
            status_code=400, 
            detail=f"Folder does not exist or is unreadable: {resolved_path}"
        )
        
    target_folder = resolved_path
    # Safeguards
    total_size = 0
    file_count = 0
    for root, _, files in os.walk(target_folder):
        for f in files:
            file_count += 1
            total_size += os.path.getsize(os.path.join(root, f))
            
    total_mb = total_size / (1024 * 1024)
    if total_mb > settings.max_dataset_size_mb:
        raise HTTPException(status_code=400, detail=f"Dataset too large ({total_mb:.1f} MB). Max allowed is {settings.max_dataset_size_mb} MB.")
    if file_count > settings.max_files_count:
        raise HTTPException(status_code=400, detail=f"Too many files ({file_count}). Max allowed is {settings.max_files_count}.")

    background_tasks.add_task(run_indexing_pipeline, target_folder)
    return {"message": f"Indexing started in the background for {target_folder}."}

@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    total = db.query(FileRecord).count()
    done = db.query(FileRecord).filter(FileRecord.status == "DONE").count()
    failed = db.query(FileRecord).filter(FileRecord.status == "FAILED").count()
    pending = db.query(FileRecord).filter(FileRecord.status == "PENDING").count()
    processing = db.query(FileRecord).filter(FileRecord.status == "PROCESSING").count()
    
    return {
        "total": total,
        "done": done,
        "failed": failed,
        "pending": pending,
        "processing": processing
    }

def format_size(size_in_bytes):
    if not size_in_bytes: return "Unknown Size"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"

@router.post("/search", response_model=List[SearchResult])
def search(request: SearchRequest, db: Session = Depends(get_db)):
    collection = get_collection()
    try:
        query_embedding = embedding_service.embed_text(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to process query.")
        
    where_clause = None
    if request.file_types and len(request.file_types) > 0:
        if len(request.file_types) == 1:
            where_clause = {"type": request.file_types[0]}
        else:
            where_clause = {"type": {"$in": request.file_types}}
            
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=request.limit * 10,  # Fetch a large pool to filter from
        where=where_clause,
        include=["metadatas", "distances"]
    )
    
    if not results['ids'][0]:
        return []
        
    unique_results = {}
    for i, meta in enumerate(results['metadatas'][0]):
        distance = results['distances'][0][i]
        item_type = meta['type']
        
        # Modality Normalization:
        if item_type == "pdf":
            norm_dist = (distance - 0.1) / 0.3
        elif item_type in ["image", "video"]:
            # Relaxed bounds so valid matches aren't incorrectly hidden
            norm_dist = (distance - 0.5) / 0.35
        else:
            norm_dist = distance
            
        norm_dist = max(0.0, min(1.0, norm_dist))
        score = 1.0 - norm_dist
        
        # Filter out extremely low-confidence matches
        if score <= 0.01:
            continue
            
        filepath = meta['filepath']
        
        if filepath not in unique_results or unique_results[filepath].score < score:
            unique_results[filepath] = SearchResult(
                filepath=filepath,
                filename=meta['filename'],
                type=item_type,
                score=round(score, 4),
                parent_id=meta.get('parent_id')
            )
            
    # Now attach sizes from SQLite
    filepaths = list(unique_results.keys())
    if filepaths:
        db_records = db.query(FileRecord.filepath, FileRecord.size_bytes).filter(FileRecord.filepath.in_(filepaths)).all()
        size_map = {r.filepath: r.size_bytes for r in db_records}
        for res in unique_results.values():
            res.size_bytes = size_map.get(res.filepath)
            res.formatted_size = format_size(res.size_bytes)
            
    sorted_results = sorted(unique_results.values(), key=lambda x: x.score, reverse=True)
    return sorted_results[:request.limit]

@router.get("/file")
def serve_file(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

@router.post("/open")
def open_file_location(request: OpenRequest):
    try:
        path = os.path.normpath(request.filepath)
        if os.name == 'nt':
            # Windows: Open explorer and select the file
            subprocess.Popen(f'explorer /select,"{path}"')
        elif sys.platform == 'darwin':
            # macOS: Reveal in Finder
            subprocess.Popen(['open', '-R', path])
        else:
            # Linux: Open the directory
            subprocess.Popen(['xdg-open', os.path.dirname(path)])
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to open file location: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/folders")
def get_indexed_folders(db: Session = Depends(get_db)):
    try:
        records = db.query(FileRecord.filepath).all()
        folder_counts = {}
        for (filepath,) in records:
            dir_path = os.path.dirname(filepath)
            folder_counts[dir_path] = folder_counts.get(dir_path, 0) + 1
        
        folders = [{"path": path, "count": count} for path, count in sorted(folder_counts.items(), key=lambda x: x[1], reverse=True)]
        return {"folders": folders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
def reset_index(db: Session = Depends(get_db)):
    try:
        # Clear SQLite DB
        db.query(FileRecord).delete()
        db.commit()
        
        # Clear ChromaDB
        from app.db.vector_store import reset_collection
        reset_collection()
        
        return {"success": True, "message": "Index completely reset."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
