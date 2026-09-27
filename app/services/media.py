import cv2
from PIL import Image
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def extract_video_keyframes(filepath: str, interval_seconds: int = None) -> list[Image.Image]:
    """
    Extracts keyframes from a video file at a specified interval.
    Returns a list of PIL Images.
    """
    interval_seconds = interval_seconds or settings.video_frame_interval_seconds
    
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {filepath}")
        
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        logger.warning(f"FPS is 0 for {filepath}. Assuming 30.")
        fps = 30
        
    frame_interval = int(fps * interval_seconds)
    if frame_interval <= 0:
        frame_interval = 1
        
    keyframes = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            # cv2 reads in BGR, convert to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            keyframes.append(pil_img)
            
        frame_count += 1
        
    cap.release()
    return keyframes

import fitz  # PyMuPDF
import io

import pytesseract

def extract_pdf_content(filepath: str) -> tuple[str, list[Image.Image]]:
    """
    Extracts text from a PDF. If a page has no native text (e.g. scanned), it falls back
    to Tesseract OCR. If OCR fails or yields no text, it falls back to extracting the page as an image.
    """
    text_content = []
    image_content = []
    
    try:
        doc = fitz.open(filepath)
    except Exception as e:
        raise ValueError(f"Could not open PDF {filepath}: {e}")
        
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text().strip()
        
        if page_text:
            text_content.append(page_text)
        else:
            logger.info(f"No native text on page {page_num} of {filepath}. Attempting OCR...")
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                
                # Attempt OCR
                ocr_text = pytesseract.image_to_string(img).strip()
                if ocr_text:
                    logger.info(f"OCR successfully extracted text from page {page_num}.")
                    text_content.append(ocr_text)
                else:
                    logger.info(f"OCR found no text on page {page_num}. Storing as image.")
                    image_content.append(img)
            except Exception as e:
                logger.warning(f"OCR or Image extraction failed for page {page_num}: {e}")
                
    doc.close()
    return "\n".join(text_content), image_content
