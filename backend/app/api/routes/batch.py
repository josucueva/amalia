"""
Batch processing routes for unattended pipeline creation and export.
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import FileResponse
import structlog

from app.models.batch import (
    BatchProcessRequest,
    BatchManifestRequest,
    BatchScanRequest,
    BatchGenerateManifestRequest,
    BatchValidateManifestRequest,
    BatchGenerateManifestResponse,
    BatchValidateManifestResponse,
    BatchRerunFailedRequest,
    BatchSubmitResponse,
    BatchJobStatusResponse,
    BatchJobResultsResponse,
    BatchArtifactListResponse,
    BatchJobStatus,
    BatchJobProgress,
    BatchJobItemResult,
)
from app.services.batch_processor import BatchProcessorError

logger = structlog.get_logger()
router = APIRouter(prefix="/api/batch", tags=["batch"])


def _raise_structured_http_error(
    *,
    status_code: int,
    code: str,
    category: str,
    message: str,
    details: dict | None = None,
):
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "category": category,
            "message": message,
            "details": details or {},
        },
    )


def _handle_batch_error(exc: Exception, fallback_code: str, fallback_message: str):
    if isinstance(exc, BatchProcessorError):
        _raise_structured_http_error(
            status_code=exc.status_code,
            code=exc.code,
            category=exc.category,
            message=str(exc),
            details=exc.details,
        )

    if isinstance(exc, (ValueError, FileNotFoundError)):
        _raise_structured_http_error(
            status_code=400,
            code="validation_error",
            category="validation",
            message=str(exc),
        )

    logger.error(fallback_message, error=str(exc))
    _raise_structured_http_error(
        status_code=500,
        code=fallback_code,
        category="execution",
        message=str(exc),
    )


def get_batch_processor(req: Request):
    """Get batch processor from app state."""
    processor = getattr(req.app.state, "batch_processor", None)
    if not processor:
        raise HTTPException(status_code=500, detail="Batch processor not initialized")
    return processor


@router.post(
    "/process",
    response_model=BatchSubmitResponse,
    responses={500: {"description": "Batch processor error"}},
)
async def submit_batch_job(request_data: BatchProcessRequest, request: Request):
    """Submit a batch job for asynchronous processing."""
    try:
        processor = get_batch_processor(request)
        idempotency_key = request.headers.get("Idempotency-Key")
        payload = request_data.model_dump(mode="json")
        job = await processor.submit_job_idempotent(
            idempotency_key=idempotency_key,
            scope="process",
            request_payload=payload,
            submit_operation=lambda: processor.submit_job(request_data),
        )
        await processor.record_submission_audit(
            job["id"],
            idempotency_key=idempotency_key,
            scope="process",
            replayed=job.get("_idempotency_replayed", False),
        )
        return BatchSubmitResponse(
            batch_job_id=job["id"],
            status=BatchJobStatus(job["status"]),
            total_datasets=len(job["items"]),
            created_at=job["created_at"],
        )
    except Exception as exc:
        _handle_batch_error(exc, "batch_submit_failed", "Failed to submit batch job")


@router.post(
    "/process-from-manifest",
    response_model=BatchSubmitResponse,
    responses={400: {"description": "Invalid manifest/filter request"}, 500: {"description": "Batch processor error"}},
)
async def submit_batch_from_manifest(
    request_data: BatchManifestRequest,
    request: Request,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
):
    """Submit a batch job by loading datasets from a JSON/CSV manifest."""
    try:
        processor = get_batch_processor(request)
        payload = request_data.model_dump(mode="json")
        job = await processor.submit_job_idempotent(
            idempotency_key=idempotency_key,
            scope="process-from-manifest",
            request_payload=payload,
            submit_operation=lambda: processor.submit_job_from_manifest(request_data),
        )
        await processor.record_submission_audit(
            job["id"],
            idempotency_key=idempotency_key,
            scope="process-from-manifest",
            replayed=job.get("_idempotency_replayed", False),
        )
        return BatchSubmitResponse(
            batch_job_id=job["id"],
            status=BatchJobStatus(job["status"]),
            total_datasets=len(job["items"]),
            created_at=job["created_at"],
        )
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_submit_manifest_failed",
            "Failed to submit manifest batch job",
        )


@router.post(
    "/scan-and-launch",
    response_model=BatchSubmitResponse,
    responses={400: {"description": "Invalid scan/filter request"}, 500: {"description": "Batch processor error"}},
)
async def submit_batch_from_scan(
    request_data: BatchScanRequest,
    request: Request,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
):
    """Scan dataset directories and launch a batch job in one request."""
    try:
        processor = get_batch_processor(request)
        payload = request_data.model_dump(mode="json")
        job = await processor.submit_job_idempotent(
            idempotency_key=idempotency_key,
            scope="scan-and-launch",
            request_payload=payload,
            submit_operation=lambda: processor.submit_job_from_scan(request_data),
        )
        await processor.record_submission_audit(
            job["id"],
            idempotency_key=idempotency_key,
            scope="scan-and-launch",
            replayed=job.get("_idempotency_replayed", False),
        )
        return BatchSubmitResponse(
            batch_job_id=job["id"],
            status=BatchJobStatus(job["status"]),
            total_datasets=len(job["items"]),
            created_at=job["created_at"],
        )
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_submit_scan_failed",
            "Failed to submit scan batch job",
        )


@router.post(
    "/generate-manifest",
    response_model=BatchGenerateManifestResponse,
    responses={400: {"description": "Invalid scan/filter request"}, 500: {"description": "Batch processor error"}},
)
async def generate_manifest_from_scan(
    request_data: BatchGenerateManifestRequest, request: Request
):
    """Generate a JSON manifest file by scanning dataset directories."""
    try:
        processor = get_batch_processor(request)
        result = processor.generate_manifest_from_scan(request_data)
        return BatchGenerateManifestResponse(
            manifest_path=result["manifest_path"],
            total_datasets=len(result["datasets"]),
            datasets=result["datasets"],
        )
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_generate_manifest_failed",
            "Failed to generate manifest",
        )


@router.post(
    "/validate-manifest",
    response_model=BatchValidateManifestResponse,
    responses={400: {"description": "Invalid manifest request"}, 500: {"description": "Batch processor error"}},
)
async def validate_manifest(
    request_data: BatchValidateManifestRequest, request: Request
):
    """Validate manifest file structure and referenced dataset files."""
    try:
        processor = get_batch_processor(request)
        result = processor.validate_manifest(request_data)
        return BatchValidateManifestResponse(**result)
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_validate_manifest_failed",
            "Failed to validate manifest",
        )


@router.get(
    "/{job_id}",
    response_model=BatchJobStatusResponse,
    responses={404: {"description": "Batch job not found"}, 500: {"description": "Batch processor error"}},
)
async def get_batch_job_status(job_id: str, request: Request):
    """Get a high-level status for a batch job."""
    processor = get_batch_processor(request)
    job = await processor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Batch job {job_id} not found")

    progress = BatchJobProgress(**job.get("progress", {}))

    return BatchJobStatusResponse(
        batch_job_id=job["id"],
        status=BatchJobStatus(job["status"]),
        progress=progress,
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        cancel_requested=job.get("cancel_requested", False),
        tags=job.get("tags", []),
        artifact_zip_ready=job.get("artifact_zip_ready", False),
        artifact_zip_path=job.get("artifact_zip_path"),
        artifact_zip_download_url=(
            f"/api/batch/{job_id}/artifacts/download"
            if job.get("artifact_zip_ready", False)
            else None
        ),
    )


@router.get(
    "/monitoring/report",
    responses={500: {"description": "Batch processor error"}},
)
async def get_batch_monitoring_report(request: Request):
    """Get monitoring report for active and historical batch activity."""
    try:
        processor = get_batch_processor(request)
        return await processor.get_monitoring_report()
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_monitoring_report_failed",
            "Failed to build batch monitoring report",
        )


@router.get(
    "/{job_id}/monitoring",
    responses={404: {"description": "Batch job not found"}, 500: {"description": "Batch processor error"}},
)
async def get_batch_job_monitoring(job_id: str, request: Request):
    """Get monitoring report for one batch job."""
    try:
        processor = get_batch_processor(request)
        return await processor.get_monitoring_report(job_id=job_id)
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_job_monitoring_report_failed",
            "Failed to build batch job monitoring report",
        )


@router.get(
    "/{job_id}/results",
    response_model=BatchJobResultsResponse,
    responses={404: {"description": "Batch job not found"}, 500: {"description": "Batch processor error"}},
)
async def get_batch_job_results(job_id: str, request: Request):
    """Get detailed item-level results for a batch job."""
    processor = get_batch_processor(request)
    job = await processor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Batch job {job_id} not found")

    items = [BatchJobItemResult(**item) for item in job.get("items", [])]
    progress = BatchJobProgress(**job.get("progress", {}))

    return BatchJobResultsResponse(
        batch_job_id=job["id"],
        status=BatchJobStatus(job["status"]),
        progress=progress,
        results=items,
        artifact_zip_ready=job.get("artifact_zip_ready", False),
        artifact_zip_path=job.get("artifact_zip_path"),
        artifact_zip_download_url=(
            f"/api/batch/{job_id}/artifacts/download"
            if job.get("artifact_zip_ready", False)
            else None
        ),
    )


@router.get(
    "/{job_id}/artifacts",
    response_model=BatchArtifactListResponse,
    responses={404: {"description": "Batch job not found"}, 500: {"description": "Batch processor error"}},
)
async def list_batch_artifacts(job_id: str, request: Request):
    """List artifact JSON files generated by a batch job."""
    processor = get_batch_processor(request)
    job = await processor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Batch job {job_id} not found")

    artifacts = processor.list_artifacts(job_id)
    return BatchArtifactListResponse(
        batch_job_id=job_id,
        artifact_count=len(artifacts),
        artifacts=artifacts,
    )


@router.get(
    "/{job_id}/artifacts/download",
    responses={404: {"description": "Batch job/artifacts not found"}, 500: {"description": "Batch processor error"}},
)
async def download_batch_artifacts(job_id: str, request: Request):
    """Download all batch artifact JSON files as a zip archive."""
    processor = get_batch_processor(request)
    job = await processor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Batch job {job_id} not found")

    zip_path = job.get("artifact_zip_path")
    if not zip_path or not Path(zip_path).exists():
        zip_path = await processor.ensure_artifact_zip(job_id, force_rebuild=True)

    if not zip_path or not Path(zip_path).exists():
        raise HTTPException(status_code=404, detail=f"No artifacts found for batch job {job_id}")

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=f"{job_id}_artifacts.zip",
    )


@router.post(
    "/{job_id}/cancel",
    responses={404: {"description": "Batch job not found"}, 500: {"description": "Batch processor error"}},
)
async def cancel_batch_job(job_id: str, request: Request):
    """Request cancellation for an active batch job."""
    processor = get_batch_processor(request)
    cancelled = await processor.cancel_job(job_id)

    if not cancelled:
        raise HTTPException(status_code=404, detail=f"Batch job {job_id} not found")

    return {
        "batch_job_id": job_id,
        "status": "cancel_requested",
    }


@router.post(
    "/{job_id}/rerun-failed",
    response_model=BatchSubmitResponse,
    responses={400: {"description": "Invalid rerun request"}, 404: {"description": "Batch job not found"}, 500: {"description": "Batch processor error"}},
)
async def rerun_failed_items(
    job_id: str,
    request_data: BatchRerunFailedRequest,
    request: Request,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
):
    """Create a new batch job from failed items of an existing batch."""
    try:
        processor = get_batch_processor(request)
        payload = {
            "job_id": job_id,
            **request_data.model_dump(mode="json"),
        }
        job = await processor.submit_job_idempotent(
            idempotency_key=idempotency_key,
            scope=f"rerun-failed:{job_id}",
            request_payload=payload,
            submit_operation=lambda: processor.submit_rerun_failed_job(
                source_job_id=job_id,
                include_skipped=request_data.include_skipped,
                limit=request_data.limit,
                tags=request_data.tags,
                settings=request_data.settings,
            ),
        )
        await processor.record_submission_audit(
            job["id"],
            idempotency_key=idempotency_key,
            scope=f"rerun-failed:{job_id}",
            replayed=job.get("_idempotency_replayed", False),
        )
        return BatchSubmitResponse(
            batch_job_id=job["id"],
            status=BatchJobStatus(job["status"]),
            total_datasets=len(job["items"]),
            created_at=job["created_at"],
        )
    except Exception as exc:
        _handle_batch_error(
            exc,
            "batch_rerun_failed_failed",
            "Failed to rerun failed items",
        )
