from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.db.database import Base

class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String, unique=True, index=True)
    file_type = Column(String)  # 'image', 'video', 'pdf'
    size_bytes = Column(Integer)
    mtime = Column(Integer)  # To store os.path.getmtime()
    content_hash = Column(String, index=True, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, PROCESSING, DONE, FAILED
    error_message = Column(Text, nullable=True)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, ForeignKey("files.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
