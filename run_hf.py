import uvicorn
import os
import gradio as gr
import spaces

# Create necessary directories for Hugging Face Spaces
os.makedirs("./data/chroma_db", exist_ok=True)
os.makedirs("./sample_media", exist_ok=True)

from app.main import app as fastapi_app

@spaces.GPU
def dummy_gpu_func(text):
    return text

html_content = """
<iframe src="/ui/index.html" width="100%" height="1000px" style="border:none;"></iframe>
"""

with gr.Blocks() as demo:
    gr.HTML(html_content)
    dummy_btn = gr.Button("Init GPU", visible=False)
    dummy_btn.click(dummy_gpu_func, inputs=dummy_btn, outputs=dummy_btn)

app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
