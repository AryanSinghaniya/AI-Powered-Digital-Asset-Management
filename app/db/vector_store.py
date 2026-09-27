import chromadb
from app.core.config import settings

# Initialize the persistent client
chroma_client = chromadb.PersistentClient(path=settings.chroma_db_dir)

collection_name = "media_embeddings"
collection = chroma_client.get_or_create_collection(
    name=collection_name,
    metadata={"hnsw:space": "cosine"}
)

def get_collection():
    return collection

def reset_collection():
    global collection
    chroma_client.delete_collection(name=collection_name)
    collection = chroma_client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
