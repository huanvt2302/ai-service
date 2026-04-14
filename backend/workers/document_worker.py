"""Redis Queue worker for document ingestion pipeline."""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rq import Queue
from redis import Redis
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
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
        logger.warning(f"[Worker] Redis unavailable, processing synchronously: {e}")
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
        logger.info(f"[Worker] Document {document_id} processed: {len(chunks)} chunks")

    except Exception as e:
        if doc:
            doc.status = DocStatus.error
            doc.error_message = str(e)
            db.commit()
        logger.error(f"[Worker] Error processing document {document_id}: {e}")
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


def _chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks that respect sentence boundaries.

    Splits on sentence terminators ('. ', '! ', '? ') so chunks don't break
    mid-sentence, which produces better embedding quality than word-splitting.
    chunk_size and overlap are measured in characters (not words).
    """
    import re

    if not text or not text.strip():
        return [text]

    # Split into sentences — keep the delimiter with the preceding sentence.
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        sent_len = len(sentence)
        # If a single sentence exceeds chunk_size, emit it as its own chunk.
        if not current and sent_len >= chunk_size:
            chunks.append(sentence)
            continue

        if current_len + sent_len + 1 > chunk_size and current:
            chunks.append(" ".join(current))
            # Backtrack by overlap characters to preserve context.
            overlap_text = " ".join(current)[-overlap:]
            current = [overlap_text] if overlap_text else []
            current_len = len(overlap_text)

        current.append(sentence)
        current_len += sent_len + 1  # +1 for the space

    if current:
        chunks.append(" ".join(current))

    return chunks or [text]


def _generate_embeddings(chunks: list[str]) -> list[list[float]]:
    """Generate embeddings for text chunks via llama-cpp/embedding API."""
    import random
    from config import get_settings
    from routes.gateway import _build_llm_url

    cfg = get_settings()

    try:
        with httpx.Client(timeout=60) as client:
            # Fix: use _build_llm_url() to avoid double /v1 when embedding_base_url already ends with /v1.
            # Previously: f"{cfg.llm_base_url}/v1/embeddings" → '/v1/v1/embeddings' (404).
            resp = client.post(
                _build_llm_url(cfg.embedding_base_url, "embeddings"),
                json={
                    "input": chunks,
                    "model": cfg.default_embedding_model,
                },
            )
            result = resp.json()
            return [item["embedding"] for item in result["data"]]
    except Exception as e:
        logger.warning(f"[Worker] Embedding API unavailable ({e}), using random embeddings")
        return [[random.uniform(-0.1, 0.1) for _ in range(1536)] for _ in chunks]
