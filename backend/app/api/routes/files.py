"""
File upload and management routes.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import structlog
import os
import uuid
import aiofiles
from pathlib import Path

from app.config import get_settings

logger = structlog.get_logger()
router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a CSV file.

    Args:
        file: Uploaded file

    Returns:
        dict: Upload status and file information
    """
    try:
        settings = get_settings()

        # Validate file type
        if not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Validate file size
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)

        if file_size_mb > settings.max_upload_size_mb:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum of {settings.max_upload_size_mb}MB",
            )

        # Generate unique filename
        file_id = uuid.uuid4().hex[:12]
        safe_filename = f"{file_id}_{file.filename}"
        file_path = Path(settings.upload_dir) / safe_filename

        # Ensure upload directory exists
        os.makedirs(settings.upload_dir, exist_ok=True)

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        logger.info(
            "File uploaded",
            filename=file.filename,
            file_id=file_id,
            size_mb=round(file_size_mb, 2),
        )

        return {
            "status": "success",
            "file_id": file_id,
            "filename": file.filename,
            "size_mb": round(file_size_mb, 2),
            "path": str(file_path),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error uploading file", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_files():
    """
    List all uploaded files.

    Returns:
        dict: List of uploaded files
    """
    try:
        settings = get_settings()
        upload_dir = Path(settings.upload_dir)

        if not upload_dir.exists():
            return {"files": [], "total": 0}

        files = []
        for file_path in upload_dir.glob("*.csv"):
            stat = file_path.stat()
            files.append(
                {
                    "filename": file_path.name,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": stat.st_ctime,
                }
            )

        return {"files": files, "total": len(files)}

    except Exception as e:
        logger.error("Error listing files", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{file_id}")
async def delete_file(file_id: str):
    """
    Delete an uploaded file.

    Args:
        file_id: File ID

    Returns:
        dict: Deletion confirmation
    """
    try:
        settings = get_settings()
        upload_dir = Path(settings.upload_dir)

        # Find file with matching ID
        file_pattern = f"{file_id}_*"
        matching_files = list(upload_dir.glob(file_pattern))

        if not matching_files:
            raise HTTPException(status_code=404, detail=f"File {file_id} not found")

        # Delete the file
        file_path = matching_files[0]
        os.remove(file_path)

        logger.info("File deleted", file_id=file_id, filename=file_path.name)

        return {"status": "deleted", "file_id": file_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting file", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
