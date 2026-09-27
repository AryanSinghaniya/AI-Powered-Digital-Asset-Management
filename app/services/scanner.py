import os
import logging
from sqlalchemy.orm import Session
from app.db.models import FileRecord
from app.services.hasher import compute_file_hash
import mimetypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.webp', # Images
    '.mp4', '.mov',                   # Videos
    '.pdf'                            # PDFs
}

def is_supported(filename: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in SUPPORTED_EXTENSIONS

def get_file_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in {'.jpg', '.jpeg', '.png', '.webp'}:
        return 'image'
    elif ext in {'.mp4', '.mov'}:
        return 'video'
    elif ext == '.pdf':
        return 'pdf'
    return 'unknown'

def scan_directory(db: Session, folder_path: str):
    """
    Scans a directory recursively and populates the DB with file records.
    Handles hashing, duplicate detection, and incremental indexing.
    """
    if not os.path.exists(folder_path):
        logger.error(f"Directory not found: {folder_path}")
        return

    logger.info(f"Scanning directory: {folder_path}")
    processed_count = 0

    for root, _, files in os.walk(folder_path):
        for file in files:
            if not is_supported(file):
                continue
            
            filepath = os.path.join(root, file)
            # Normalize path for consistency
            filepath = os.path.abspath(filepath)
            
            try:
                stat = os.stat(filepath)
                size_bytes = stat.st_size
                mtime = int(stat.st_mtime)
            except Exception as e:
                logger.error(f"Could not read stats for {filepath}: {e}")
                continue

            existing_record = db.query(FileRecord).filter(FileRecord.filepath == filepath).first()
            
            # Incremental indexing check: if size and mtime are same, and it's not FAILED, skip hashing
            if existing_record and existing_record.size_bytes == size_bytes and existing_record.mtime == mtime:
                # If we previously failed, we might want to retry, but for pure scanning phase we can just skip or mark pending
                if existing_record.status != "FAILED":
                    logger.debug(f"Skipping unchanged file: {filepath}")
                    continue
                else:
                    logger.info(f"Retrying previously failed file: {filepath}")
            
            # We need to hash it
            try:
                file_hash = compute_file_hash(filepath)
            except Exception as e:
                # Corrupted or unreadable file
                if not existing_record:
                    existing_record = FileRecord(
                        filename=file,
                        filepath=filepath,
                        file_type=get_file_type(file),
                        size_bytes=size_bytes,
                        mtime=mtime
                    )
                    db.add(existing_record)
                
                existing_record.status = "FAILED"
                existing_record.error_message = f"Failed to read/hash file: {str(e)}"
                db.commit()
                continue
            
            # Check for duplicates by hash
            duplicate_record = db.query(FileRecord).filter(
                FileRecord.content_hash == file_hash, 
                FileRecord.filepath != filepath
            ).first()

            if existing_record:
                # Update existing record
                existing_record.size_bytes = size_bytes
                existing_record.mtime = mtime
                existing_record.content_hash = file_hash
                existing_record.status = "PENDING"
                existing_record.error_message = None
                
                if duplicate_record:
                    existing_record.is_duplicate = True
                    existing_record.duplicate_of = duplicate_record.id
                    existing_record.status = "DONE"
                else:
                    existing_record.is_duplicate = False
                    existing_record.duplicate_of = None
            else:
                # Create new record
                new_record = FileRecord(
                    filename=file,
                    filepath=filepath,
                    file_type=get_file_type(file),
                    size_bytes=size_bytes,
                    mtime=mtime,
                    content_hash=file_hash,
                    status="PENDING"
                )
                if duplicate_record:
                    new_record.is_duplicate = True
                    new_record.duplicate_of = duplicate_record.id
                    new_record.status = "DONE"
                
                db.add(new_record)
            
            db.commit()
            processed_count += 1

    logger.info(f"Scan complete. Processed/Updated {processed_count} files.")
