import torch
import open_clip
from PIL import Image
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        logger.info(f"Loading CLIP model {settings.clip_model_name} ({settings.clip_pretrained})...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # open_clip can sometimes take a while to download weights on first run
        model, _, preprocess = open_clip.create_model_and_transforms(
            settings.clip_model_name, 
            pretrained=settings.clip_pretrained
        )
        self.model = model.to(self.device)
        self.model.eval()
        self.preprocess = preprocess
        
        # Text tokenizer for future search queries
        self.tokenizer = open_clip.get_tokenizer(settings.clip_model_name)
        logger.info("CLIP model loaded successfully.")

    def embed_pil_image(self, image: Image.Image) -> list[float]:
        try:
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            with torch.no_grad():
                image_features = self.model.encode_image(image_input)
                image_features /= image_features.norm(dim=-1, keepdim=True)
            return image_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logger.error(f"Failed to embed PIL image: {e}")
            raise

    def embed_image(self, image_path: str) -> list[float]:
        try:
            image = Image.open(image_path).convert("RGB")
            return self.embed_pil_image(image)
        except Exception as e:
            logger.error(f"Failed to embed image {image_path}: {e}")
            raise

    def embed_text(self, text: str) -> list[float]:
        try:
            # CLIP has a max sequence length of 77 tokens
            text_tokens = self.tokenizer([text]).to(self.device)
            with torch.no_grad():
                text_features = self.model.encode_text(text_tokens)
                text_features /= text_features.norm(dim=-1, keepdim=True)
            return text_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise

embedding_service = EmbeddingService()
