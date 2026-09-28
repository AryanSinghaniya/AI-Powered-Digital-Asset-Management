import os
import cv2
import fitz # PyMuPDF
import numpy as np
import shutil

src_dir = r"C:\Users\hp\.gemini\antigravity-ide\brain\26b3391c-9d98-4777-af32-fa4cd60e6e07"
dest_dir = r"C:\Users\hp\OneDrive\Desktop\Assignmen_Ai_managment\dam_project\demo_media"

# 1. Copy images
for file in os.listdir(src_dir):
    if file.endswith(".jpg"):
        shutil.copy(os.path.join(src_dir, file), os.path.join(dest_dir, file))
        print(f"Copied {file}")

# 2. Create PDF
pdf_path = os.path.join(dest_dir, "residential_brochure.pdf")
doc = fitz.open()
page = doc.new_page()
page.insert_text((50, 50), "Brochures related to residential projects and modern real estate.", fontsize=14)
page.insert_text((50, 100), "This is a sample document for the DAM system demo.", fontsize=12)
doc.save(pdf_path)
print("Created PDF")

# 3. Create MP4 Video (a simple 2-second video with text)
video_path = os.path.join(dest_dir, "construction_activity.mp4")
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480))

for i in range(60): # 2 seconds
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40) # Dark gray background
    cv2.putText(frame, "Construction Activity", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Draw a moving square to simulate "activity"
    cv2.rectangle(frame, (100 + i*5, 300), (150 + i*5, 350), (0, 165, 255), -1)
    out.write(frame)

out.release()
print("Created Video")
