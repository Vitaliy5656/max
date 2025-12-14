"""
Documents (RAG) Router for MAX AI API.

Endpoints:
- GET /api/documents
- POST /api/documents/upload
- DELETE /api/documents/{doc_id}
"""
import os
import tempfile

from fastapi import APIRouter, UploadFile, File

from src.core.rag import rag

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents():
    """List all indexed documents."""
    docs = await rag.list_documents()
    return [{
        "id": str(d.id),
        "name": d.filename,
        "size": f"{d.chunk_count * 500} chars",  # Approximate
        "type": d.filename.split(".")[-1] if "." in d.filename else "txt",
        "chunks": d.chunk_count,
        "status": "indexed"
    } for d in docs]


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and index a document."""
    # Save to temp file (Streamed)
    temp_path = os.path.join(tempfile.gettempdir(), file.filename)
    # Optimization: Read in chunks to avoid memory spike
    with open(temp_path, 'wb') as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            f.write(chunk)
    
    try:
        # Index document
        doc = await rag.add_document(temp_path)
        return {"id": str(doc.id), "name": doc.filename, "status": "indexed"}
    finally:
        # P1 fix: Cleanup temp file to prevent disk leak
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document."""
    await rag.remove_document(doc_id)
    return {"success": True}
