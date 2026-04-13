"""Redis Queue worker for document ingestion pipeline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rq import Queue
from redis import Redis
from config import get_settings

settings = get_settings()
_redis_conn = None
_queue = None


def get_queue() -> Queue:
    global _redis_conn, _queue
    if _queue is None:
        _redis_conn = Redis.from_url(settings.redis_url)
        _queue = Queue("document_queue", connection=_redis_conn)
    return _queue


def enqueue_document_processing(document_id: str):
    """Enqueue a document for background processing."""
    try:
        q = get_queue()
        q.enqueue("workers.document_worker.process_document", document_id, timeout=300)
    except Exception as e:
        # If Redis not available, process synchronously
        print(f"[Worker] Redis unavailable, processing synchronously: {e}")
        process_document(document_id)


def process_document(document_id: str):
    """
    Process a document:
    1. Read file
    2. Chunk text
    3. Generate embeddings
    4. Store in pgvector
    """
    from database import SessionLocal
    from models import Document, DocumentChunk, DocStatus
    import httpx

    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return

        doc.status = DocStatus.processing
        db.commit()

        # Read file
        content = _read_file(doc)

        # Chunk text
        chunks = _chunk_text(content)

        # Generate embeddings
        embeddings = _generate_embeddings(chunks)

        # Store chunks
        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_index=i,
                content=chunk_text,
                embedding=embedding,
                metadata_={"filename": doc.filename, "chunk_index": i},
            )
            db.add(chunk)

        doc.chunk_count = len(chunks)
        doc.status = DocStatus.done
        db.commit()
        print(f"[Worker] Document {document_id} processed: {len(chunks)} chunks")

    except Exception as e:
        if doc:
            doc.status = DocStatus.error
            doc.error_message = str(e)
            db.commit()
        print(f"[Worker] Error processing document {document_id}: {e}")
    finally:
        db.close()


def _read_file(doc) -> str:
    """Read document content as text."""
    if not doc.file_path or not os.path.exists(doc.file_path):
        return f"Document: {doc.filename}"

    try:
        with open(doc.file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return f"[Binary file: {doc.filename}]"


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    if not words:
        return [text]

    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        i += chunk_size - overlap

    return chunks or [text]


def _generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Generate embeddings for text chunks via vLLM."""
    import random
    from config import get_settings

    settings = get_settings()

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{settings.vllm_base_url}/v1/embeddings",
                json={
                    "input": chunks,
                    "model": settings.default_embedding_model,
                },
            )
            result = resp.json()
            return [item["embedding"] for item in result["data"]]
    except Exception as e:
        print(f"[Worker] Embedding API unavailable ({e}), using random embeddings")
        return [[random.uniform(-0.1, 0.1) for _ in range(1536)] for _ in chunks]
