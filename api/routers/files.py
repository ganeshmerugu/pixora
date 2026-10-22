from __future__ import annotations
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from pixora.storage import save_file, get_file

router = APIRouter(prefix="/files", tags=["files"])


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    data = await file.read()
    file_id = save_file(file.filename or "unknown", data, file.content_type or "")
    return {
        "file_id": file_id,
        "filename": file.filename,
        "size_bytes": len(data),
        "mime_type": file.content_type,
    }


@router.get("/{file_id}")
async def get_file_info(file_id: str):
    f = get_file(file_id)
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": f["id"],
        "filename": f["filename"],
        "size_bytes": f["size_bytes"],
        "mime_type": f["mime_type"],
    }
