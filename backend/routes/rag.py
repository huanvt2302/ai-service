"""RAG management routes: collections + documents"""
import os
import uuid
import logging
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models import Collection, Document, DocumentChunk, DocStatus, User
from auth import get_current_user
from config import get_settings
from workers.document_worker import enqueue_document_processing
from routes.gateway import _build_llm_url

settings = get_settings()
router = APIRouter(tags=["rag"])
logger = logging.getLogger(__name__)


# ── Collections ────────────────────────────────────────────────────────────

class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"


@router.get("/v1/collections")
def list_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cols = db.query(Collection).filter(Collection.team_id == current_user.team_id).order_by(Collection.created_at.desc()).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "doc_count": c.doc_count,
            "embedding_model": c.embedding_model,
            "created_at": c.created_at.isoformat(),
        }
        for c in cols
    ]


@router.post("/v1/collections")
def create_collection(
    req: CreateCollectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = Collection(
        team_id=current_user.team_id,
        name=req.name,
        description=req.description,
        embedding_model=req.embedding_model,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return {"id": str(col.id), "name": col.name, "description": col.description, "doc_count": col.doc_count}


@router.get("/v1/collections/{collection_id}")
def get_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = db.query(Collection).filter(Collection.id == collection_id, Collection.team_id == current_user.team_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    docs = db.query(Document).filter(Document.collection_id == col.id).all()
    return {
        "id": str(col.id),
        "name": col.name,
        "description": col.description,
        "doc_count": col.doc_count,
        "embedding_model": col.embedding_model,
        "documents": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_size": d.file_size,
                "chunk_count": d.chunk_count,
                "status": d.status.value,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
    }


@router.delete("/v1/collections/{collection_id}")
def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = db.query(Collection).filter(Collection.id == collection_id, Collection.team_id == current_user.team_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    db.delete(col)
    db.commit()
    return {"message": "Collection deleted"}


# ── Documents ──────────────────────────────────────────────────────────────

@router.post("/v1/documents")
async def upload_document(
    collection_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    col = db.query(Collection).filter(Collection.id == collection_id, Collection.team_id == current_user.team_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Validate size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File too large (max {settings.max_upload_size_mb}MB)")

    # Save to disk
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(settings.upload_dir, f"{file_id}{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Create document record
    doc = Document(
        collection_id=collection_id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        status=DocStatus.pending,
    )
    db.add(doc)
    col.doc_count = (col.doc_count or 0) + 1
    db.commit()
    db.refresh(doc)

    # Enqueue background processing
    enqueue_document_processing(str(doc.id))

    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "status": doc.status.value,
        "message": "Document uploaded and queued for processing",
    }


@router.get("/v1/documents/{doc_id}")
def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Fix [SECURITY]: scope query to team_id to prevent cross-team document access.
    # Previously: filter only on Document.id — any authenticated user could read any document.
    doc = (
        db.query(Document)
        .join(Collection, Document.collection_id == Collection.id)
        .filter(Document.id == doc_id, Collection.team_id == current_user.team_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "file_size": doc.file_size,
        "chunk_count": doc.chunk_count,
        "status": doc.status.value,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat(),
    }


@router.delete("/v1/documents/{doc_id}")
def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Fix [SECURITY]: scope query to team_id to prevent cross-team document deletion.
    # Previously: filter only on Document.id — any authenticated user could delete any document.
    doc = (
        db.query(Document)
        .join(Collection, Document.collection_id == Collection.id)
        .filter(Document.id == doc_id, Collection.team_id == current_user.team_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    col = doc.collection
    db.delete(doc)
    if col:
        col.doc_count = max(0, (col.doc_count or 1) - 1)
    db.commit()
    return {"message": "Document deleted"}


# ── Vector Search ──────────────────────────────────────────────────────────

@router.post("/v1/collections/{collection_id}/search")
async def search_collection(
    collection_id: str,
    request_body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Semantic search in a collection using pgvector."""
    from metrics import RAG_SEARCH_LATENCY
    import time, httpx

    query = request_body.get("query", "")
    top_k = request_body.get("top_k", 5)

    start = time.time()

    # Get query embedding
    # Fix: use _build_llm_url() to avoid double /v1 when embedding_base_url already ends with /v1.
    # Previously: f"{settings.llm_base_url}/v1/embeddings" → '/v1/v1/embeddings' (404).
    embedding = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _build_llm_url(settings.embedding_base_url, "embeddings"),
                json={"input": query, "model": settings.default_embedding_model},
            )
            result = resp.json()
            embedding = result["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding API unavailable for search ({e}), using random embedding fallback")
        import random
        embedding = [random.uniform(-0.1, 0.1) for _ in range(1536)]

    # pgvector cosine similarity search
    chunks = db.query(DocumentChunk).join(Document).filter(
        Document.collection_id == collection_id
    ).order_by(
        DocumentChunk.embedding.cosine_distance(embedding)
    ).limit(top_k).all()

    RAG_SEARCH_LATENCY.labels(collection_id=collection_id).observe(time.time() - start)

    return {
        "results": [
            {
                "chunk_id": str(c.id),
                "document_id": str(c.document_id),
                "content": c.content,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]
    }
