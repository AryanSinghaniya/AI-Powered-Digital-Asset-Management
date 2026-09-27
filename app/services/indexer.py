import logging
from sqlalchemy.orm import Session
from app.db.models import FileRecord
from app.db.vector_store import get_collection
from app.services.embedding import embedding_service
from app.services.media import extract_video_keyframes, extract_pdf_content

logger = logging.getLogger(__name__)

def process_pending_images(db: Session):
    collection = get_collection()
    
    # Get pending images that are not duplicates
    pending_records = db.query(FileRecord).filter(
        FileRecord.status == "PENDING",
        FileRecord.file_type == "image",
        FileRecord.is_duplicate == False
    ).all()
    
    if not pending_records:
        logger.info("No pending images to process.")
        return

    logger.info(f"Found {len(pending_records)} pending images. Processing...")

    for record in pending_records:
        try:
            record.status = "PROCESSING"
            db.commit()
            
            # Extract embedding
            embedding = embedding_service.embed_image(record.filepath)
            
            # Store in ChromaDB
            collection.add(
                ids=[str(record.id)],
                embeddings=[embedding],
                metadatas=[{"filepath": record.filepath, "filename": record.filename, "type": "image"}]
            )
            
            record.status = "DONE"
            db.commit()
            logger.info(f"Successfully processed image: {record.filename}")
            
        except Exception as e:
            logger.error(f"Error processing image {record.filename}: {e}")
            db.rollback()
            
            failed_record = db.query(FileRecord).filter(FileRecord.id == record.id).first()
            if failed_record:
                failed_record.status = "FAILED"
                failed_record.error_message = str(e)
                db.commit()

def process_pending_videos(db: Session):
    collection = get_collection()
    
    pending_records = db.query(FileRecord).filter(
        FileRecord.status == "PENDING",
        FileRecord.file_type == "video",
        FileRecord.is_duplicate == False
    ).all()
    
    if not pending_records:
        logger.info("No pending videos to process.")
        return

    logger.info(f"Found {len(pending_records)} pending videos. Processing...")

    for record in pending_records:
        try:
            record.status = "PROCESSING"
            db.commit()
            
            keyframes = extract_video_keyframes(record.filepath)
            
            if not keyframes:
                raise ValueError("No frames could be extracted from video.")
                
            ids = []
            embeddings = []
            metadatas = []
            
            for i, frame in enumerate(keyframes):
                emb = embedding_service.embed_pil_image(frame)
                ids.append(f"{record.id}_frame_{i}")
                embeddings.append(emb)
                metadatas.append({
                    "filepath": record.filepath,
                    "filename": record.filename,
                    "type": "video",
                    "parent_id": record.id,
                    "frame_index": i
                })
                
            collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)
            
            record.status = "DONE"
            db.commit()
            logger.info(f"Successfully processed video: {record.filename} ({len(keyframes)} frames)")
            
        except Exception as e:
            logger.error(f"Error processing video {record.filename}: {e}")
            db.rollback()
            
            failed_record = db.query(FileRecord).filter(FileRecord.id == record.id).first()
            if failed_record:
                failed_record.status = "FAILED"
                failed_record.error_message = str(e)
                db.commit()

def chunk_text(text: str, chunk_size: int = 50) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))
    return chunks

def process_pending_pdfs(db: Session):
    collection = get_collection()
    
    pending_records = db.query(FileRecord).filter(
        FileRecord.status == "PENDING",
        FileRecord.file_type == "pdf",
        FileRecord.is_duplicate == False
    ).all()
    
    if not pending_records:
        logger.info("No pending PDFs to process.")
        return

    logger.info(f"Found {len(pending_records)} pending PDFs. Processing...")

    for record in pending_records:
        try:
            record.status = "PROCESSING"
            db.commit()
            
            extracted_text, extracted_images = extract_pdf_content(record.filepath)
            
            if not extracted_text.strip() and not extracted_images:
                raise ValueError("No text or images could be extracted from PDF.")
                
            text_chunks = chunk_text(extracted_text, chunk_size=50) if extracted_text.strip() else []
            
            ids = []
            embeddings = []
            metadatas = []
            
            for i, chunk in enumerate(text_chunks):
                if not chunk.strip():
                    continue
                emb = embedding_service.embed_text(chunk)
                ids.append(f"{record.id}_chunk_{i}")
                embeddings.append(emb)
                metadatas.append({
                    "filepath": record.filepath,
                    "filename": record.filename,
                    "type": "pdf",
                    "parent_id": record.id,
                    "chunk_index": i,
                    "text": chunk
                })
                
            for i, img in enumerate(extracted_images):
                emb = embedding_service.embed_pil_image(img)
                ids.append(f"{record.id}_img_{i}")
                embeddings.append(emb)
                metadatas.append({
                    "filepath": record.filepath,
                    "filename": record.filename,
                    "type": "pdf", # Search API handles it seamlessly if left as pdf
                    "parent_id": record.id,
                    "image_index": i
                })
                
            if ids:
                collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)
            
            record.status = "DONE"
            db.commit()
            logger.info(f"Successfully processed PDF: {record.filename} ({len(ids)} chunks)")
            
        except Exception as e:
            logger.error(f"Error processing PDF {record.filename}: {e}")
            db.rollback()
            
            failed_record = db.query(FileRecord).filter(FileRecord.id == record.id).first()
            if failed_record:
                failed_record.status = "FAILED"
                failed_record.error_message = str(e)
                db.commit()
