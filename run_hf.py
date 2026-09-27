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

demo = gr.Interface(fn=dummy_gpu_func, inputs="text", outputs="text")
app = gr.mount_gradio_app(fastapi_app, demo, path="/dummy")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
