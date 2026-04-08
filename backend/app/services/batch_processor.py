"""
Asynchronous batch processor for unattended pipeline generation and export.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Awaitable

import structlog

from app.database import get_db
from app.models.batch import (
    BatchItemStatus,
    BatchJobStatus,
    DatasetBatchItem,
    BatchManifestRequest,
    BatchProcessSettings,
    BatchProcessRequest,
    BatchScanRequest,
    BatchGenerateManifestRequest,
    BatchValidateManifestRequest,
    ManifestValidationIssue,
    BatchJobProgress,
)
from app.services.batch_artifact_service import BatchArtifactService
from app.services.agent_pipeline import AgentPipelineService

logger = structlog.get_logger()
DEFAULT_DATA_DIR = Path("./data")


class BatchProcessorError(Exception):
    """Base error with standardized metadata for API mapping."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        category: str,
        status_code: int,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.category = category
        self.status_code = status_code
        self.details = details or {}


class BatchValidationError(BatchProcessorError):
    """Validation-layer error (bad inputs/paths/filters)."""

    def __init__(self, message: str, *, code: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message,
            code=code,
            category="validation",
            status_code=400,
            details=details,
        )


class BatchConflictError(BatchProcessorError):
    """Concurrency/idempotency conflict error."""

    def __init__(self, message: str, *, code: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message,
            code=code,
            category="concurrency",
            status_code=409,
            details=details,
        )


class BatchInfrastructureError(BatchProcessorError):
    """Infrastructure/runtime consistency error."""

    def __init__(self, message: str, *, code: str, details: Optional[dict[str, Any]] = None):
        super().__init__(
            message,
            code=code,
            category="infrastructure",
            status_code=503,
            details=details,
        )


class BatchProcessorService:
    """Background queue + worker processor for batch jobs."""

    SUPPORTED_TASK_TYPES = {"classification", "regression"}
    SUPPORTED_TIERS = {"easy", "mid", "hard"}

    def __init__(
        self,
        llm_service,
        agent_registry,
        mcp_server_service,
        session_manager,
        settings,
    ):
        self.llm_service = llm_service
        self.agent_registry = agent_registry
        self.mcp_server_service = mcp_server_service
        self.session_manager = session_manager
        self.settings = settings

        self.collection_name = "batch_jobs"
        self.idempotency_collection_name = "batch_job_idempotency"
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._running = False
        self.artifact_service = BatchArtifactService(settings.batch_artifacts_dir)

    def _collection(self):
        return get_db()[self.collection_name]

    def _idempotency_collection(self):
        return get_db()[self.idempotency_collection_name]

    def _hash_idempotency_key(self, key: str) -> str:
        """Hash idempotency key before storing in job audit fields."""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def record_submission_audit(
        self,
        job_id: str,
        *,
        idempotency_key: Optional[str],
        scope: str,
        replayed: bool,
    ) -> None:
        """Persist submission metadata for observability/audit."""
        if not idempotency_key:
            await self._collection().update_one(
                {"id": job_id},
                {
                    "$set": {
                        "audit.submission": {
                            "scope": scope,
                            "idempotency_key_provided": False,
                            "idempotency_replayed": False,
                        }
                    }
                },
            )
            return

        await self._collection().update_one(
            {"id": job_id},
            {
                "$set": {
                    "audit.submission": {
                        "scope": scope,
                        "idempotency_key_provided": True,
                        "idempotency_key_hash": self._hash_idempotency_key(
                            idempotency_key
                        ),
                        "idempotency_replayed": replayed,
                    }
                }
            },
        )

    async def submit_job_idempotent(
        self,
        idempotency_key: Optional[str],
        scope: str,
        request_payload: dict[str, Any],
        submit_operation: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Submit a job with idempotency replay semantics when key is provided."""
        if not idempotency_key:
            job = await submit_operation()
            job["_idempotency_replayed"] = False
            job["_idempotency_scope"] = scope
            return job

        request_hash = hashlib.sha256(
            json.dumps(request_payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        token_id = f"{scope}:{idempotency_key.strip()}"
        now = datetime.now(timezone.utc)

        result = await self._idempotency_collection().update_one(
            {"id": token_id},
            {
                "$setOnInsert": {
                    "id": token_id,
                    "scope": scope,
                    "idempotency_key": idempotency_key.strip(),
                    "request_hash": request_hash,
                    "status": "in_progress",
                    "created_at": now,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

        if result.upserted_id:
            try:
                job = await submit_operation()
            except Exception as exc:
                await self._idempotency_collection().update_one(
                    {"id": token_id},
                    {
                        "$set": {
                            "status": "failed",
                            "error": str(exc),
                            "updated_at": datetime.now(timezone.utc),
                        }
                    },
                )
                raise

            await self._idempotency_collection().update_one(
                {"id": token_id},
                {
                    "$set": {
                        "status": "completed",
                        "job_id": job["id"],
                        "updated_at": datetime.now(timezone.utc),
                    }
                },
            )
            job["_idempotency_replayed"] = False
            job["_idempotency_scope"] = scope
            return job

        token = await self._idempotency_collection().find_one({"id": token_id})
        if not token:
            raise BatchInfrastructureError(
                "Idempotency record could not be loaded",
                code="idempotency_record_missing",
            )

        if token.get("request_hash") != request_hash:
            raise BatchConflictError(
                "Idempotency key was already used with different payload",
                code="idempotency_key_reused_with_different_payload",
            )

        if token.get("status") == "in_progress":
            raise BatchConflictError(
                "Identical request is currently being processed",
                code="idempotency_request_in_progress",
            )

        if token.get("status") == "completed" and token.get("job_id"):
            existing_job = await self.get_job(token["job_id"])
            if not existing_job:
                raise BatchInfrastructureError(
                    "Idempotency replay referenced a missing job",
                    code="idempotency_replay_missing_job",
                    details={"job_id": token.get("job_id")},
                )
            existing_job["_idempotency_replayed"] = True
            existing_job["_idempotency_scope"] = scope
            return existing_job

        raise BatchConflictError(
            "Idempotency key is not reusable in current state",
            code="idempotency_key_not_reusable",
            details={"status": token.get("status")},
        )

    def start(self) -> None:
        """Start worker tasks."""
        if self._running:
            return

        self._running = True
        worker_count = max(1, self.settings.batch_max_workers)
        for index in range(worker_count):
            task = asyncio.create_task(self._worker_loop(index))
            self._workers.append(task)

        logger.info("Batch processor started", workers=worker_count)

    async def stop(self) -> None:
        """Stop worker tasks."""
        if not self._running:
            return

        self._running = False
        for task in self._workers:
            task.cancel()

        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        logger.info("Batch processor stopped")

    async def submit_job(
        self,
        request: BatchProcessRequest,
        source: Optional[dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist and enqueue a new job."""
        now = datetime.now(timezone.utc)
        job_id = f"batch_{now.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

        max_retries = request.settings.max_retries
        if max_retries is None:
            max_retries = self.settings.batch_item_max_retries

        items = []
        for ds in request.datasets:
            items.append(
                {
                    "dataset_id": ds.dataset_id,
                    "filename": ds.filename,
                    "file_path": ds.file_path,
                    "task_type": ds.task_type,
                    "tier": ds.tier,
                    "target_column": ds.target_column,
                    "intent": ds.intent,
                    "status": BatchItemStatus.PENDING.value,
                    "retries": 0,
                    "started_at": None,
                    "completed_at": None,
                    "duration_seconds": None,
                    "error": None,
                    "session_id": None,
                    "artifact_path": None,
                    "orchestration": None,
                }
            )

        progress = BatchJobProgress(total=len(items)).model_dump()

        doc = {
            "id": job_id,
            "status": BatchJobStatus.QUEUED.value,
            "created_at": now,
            "started_at": None,
            "completed_at": None,
            "cancel_requested": False,
            "artifact_zip_path": None,
            "artifact_zip_ready": False,
            "tags": request.tags or [],
            "settings": {
                "max_retries": max_retries,
                "fail_fast": request.settings.fail_fast,
                "create_sessions": request.settings.create_sessions,
            },
            "source": source or {"type": "direct"},
            "audit": {
                "submission": {
                    "scope": "process",
                    "idempotency_key_provided": False,
                    "idempotency_replayed": False,
                }
            },
            "metrics": {
                "queue_depth_at_submit": self._queue.qsize(),
                "job_queue_wait_seconds": None,
                "total_retries": 0,
                "items_with_duration": 0,
                "total_item_duration_seconds": 0.0,
                "avg_item_duration_seconds": None,
                "max_item_duration_seconds": None,
                "failure_reason_buckets": {},
                "last_updated_at": now,
            },
            "progress": progress,
            "items": items,
        }

        await self._collection().insert_one(doc)
        await self._queue.put(job_id)

        logger.info("Batch job queued", job_id=job_id, total_items=len(items))
        return doc

    async def submit_job_from_manifest(
        self, request: BatchManifestRequest
    ) -> Dict[str, Any]:
        """Load datasets from manifest and submit a standard batch job."""
        datasets = self.load_datasets_from_manifest(request)
        process_request = BatchProcessRequest(
            datasets=datasets,
            tags=request.tags,
            settings=request.settings,
        )
        return await self.submit_job(
            process_request,
            source={
                "type": "manifest",
                "manifest_path": request.manifest_path,
            },
        )

    async def submit_job_from_scan(self, request: BatchScanRequest) -> Dict[str, Any]:
        """Scan dataset directories and submit a standard batch job."""
        scan_signature = self._compute_signature(
            {
                "datasets_root": request.datasets_root,
                "task_type": request.task_type,
                "tier": request.tier,
                "dataset_ids": request.dataset_ids,
                "limit": request.limit,
                "file_extensions": request.file_extensions,
                "tags": request.tags,
                "settings": request.settings.model_dump(),
            }
        )
        await self._ensure_no_active_job_conflict(
            source_filter={
                "source.type": "scan",
                "source.scan_signature": scan_signature,
            },
            message="An equivalent scan-and-launch batch is already active",
            code="scan_batch_already_active",
        )

        datasets = self.scan_datasets(
            datasets_root=request.datasets_root,
            task_type=request.task_type,
            tier=request.tier,
            dataset_ids=request.dataset_ids,
            limit=request.limit,
            file_extensions=request.file_extensions,
        )
        process_request = BatchProcessRequest(
            datasets=datasets,
            tags=request.tags,
            settings=request.settings,
        )
        return await self.submit_job(
            process_request,
            source={
                "type": "scan",
                "scan_signature": scan_signature,
            },
        )

    async def submit_rerun_failed_job(
        self,
        source_job_id: str,
        include_skipped: bool = False,
        limit: Optional[int] = None,
        tags: Optional[list[str]] = None,
        settings: Optional[BatchProcessSettings] = None,
    ) -> Dict[str, Any]:
        """Create a new batch job from failed items of an existing job."""
        source_job = await self.get_job(source_job_id)
        if not source_job:
            raise BatchValidationError(
                f"Batch job {source_job_id} not found",
                code="source_batch_not_found",
            )

        await self._ensure_no_active_job_conflict(
            source_filter={
                "source.type": "rerun_failed",
                "source.source_job_id": source_job_id,
                "source.include_skipped": include_skipped,
            },
            message="A rerun-failed batch is already active for this source job",
            code="rerun_batch_already_active",
        )

        allowed_statuses = {BatchItemStatus.FAILED.value}
        if include_skipped:
            allowed_statuses.add(BatchItemStatus.SKIPPED.value)

        datasets: list[DatasetBatchItem] = []
        for item in source_job.get("items", []):
            if item.get("status") not in allowed_statuses:
                continue

            datasets.append(
                DatasetBatchItem(
                    dataset_id=item["dataset_id"],
                    filename=item["filename"],
                    file_path=item["file_path"],
                    task_type=item.get("task_type"),
                    tier=item.get("tier"),
                    target_column=item.get("target_column"),
                    intent=item.get("intent"),
                )
            )

        if limit:
            datasets = datasets[:limit]

        if not datasets:
            raise BatchValidationError(
                "No failed items found to rerun",
                code="no_failed_items_to_rerun",
            )

        inherited_settings = source_job.get("settings", {})
        resolved_settings = settings or BatchProcessSettings(
            max_retries=inherited_settings.get(
                "max_retries", self.settings.batch_item_max_retries
            ),
            fail_fast=inherited_settings.get("fail_fast", False),
            create_sessions=inherited_settings.get("create_sessions", True),
        )

        resolved_tags = tags or source_job.get("tags", [])
        rerun_tag = f"rerun_of:{source_job_id}"
        if rerun_tag not in resolved_tags:
            resolved_tags = [*resolved_tags, rerun_tag]

        request = BatchProcessRequest(
            datasets=datasets,
            tags=resolved_tags,
            settings=resolved_settings,
        )
        return await self.submit_job(
            request,
            source={
                "type": "rerun_failed",
                "source_job_id": source_job_id,
                "include_skipped": include_skipped,
            },
        )

    def generate_manifest_from_scan(
        self, request: BatchGenerateManifestRequest
    ) -> Dict[str, Any]:
        """Scan datasets and write a JSON manifest file."""
        datasets = self.scan_datasets(
            datasets_root=request.datasets_root,
            task_type=request.task_type,
            tier=request.tier,
            dataset_ids=request.dataset_ids,
            limit=request.limit,
            file_extensions=request.file_extensions,
        )

        if request.output_path:
            output_path = Path(request.output_path)
            if not output_path.is_absolute():
                output_path = Path("/app") / output_path
        else:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            output_path = (
                Path(self.settings.batch_artifacts_dir)
                / "manifests"
                / f"datasets_manifest_{timestamp}.json"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": [dataset.model_dump() for dataset in datasets],
        }
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        return {
            "manifest_path": str(output_path),
            "datasets": datasets,
        }

    def validate_manifest(
        self, request: BatchValidateManifestRequest
    ) -> Dict[str, Any]:
        """Validate manifest rows and referenced dataset files."""
        manifest_path = self._resolve_manifest_path(request.manifest_path)
        if not manifest_path.exists():
            raise BatchValidationError(
                f"Manifest not found: {manifest_path}",
                code="manifest_not_found",
            )

        extension = manifest_path.suffix.lower()
        if extension == ".json":
            rows = self._load_manifest_json(manifest_path)
        elif extension == ".csv":
            rows = self._load_manifest_csv(manifest_path)
        else:
            raise BatchValidationError(
                "Manifest must be .json or .csv",
                code="invalid_manifest_extension",
            )

        issues: list[ManifestValidationIssue] = []
        valid_rows = 0
        for index, row in enumerate(rows, start=1):
            try:
                dataset = self._normalize_manifest_row(row)
                resolved_path = self._resolve_dataset_file_path(dataset.file_path)
                if not resolved_path.exists():
                    raise FileNotFoundError(
                        f"Dataset file not found: {dataset.file_path}"
                    )
                valid_rows += 1
            except Exception as exc:
                issues.append(
                    ManifestValidationIssue(
                        row_index=index,
                        dataset_id=(
                            str(row.get("dataset_id") or row.get("id"))
                            if isinstance(row, dict)
                            else None
                        ),
                        error=str(exc),
                    )
                )

        total_rows = len(rows)
        return {
            "manifest_path": str(manifest_path),
            "total_rows": total_rows,
            "valid_rows": valid_rows,
            "invalid_rows": total_rows - valid_rows,
            "issues": issues,
        }

    def scan_datasets(
        self,
        datasets_root: Optional[str],
        task_type: Optional[str],
        tier: Optional[str],
        dataset_ids: Optional[list[str]],
        limit: Optional[int],
        file_extensions: list[str],
    ) -> list[DatasetBatchItem]:
        """Scan dataset tree and create normalized DatasetBatchItem entries."""
        root_path = self._resolve_datasets_root(datasets_root)
        if not root_path.exists():
            raise BatchValidationError(
                f"Datasets root not found: {root_path}",
                code="datasets_root_not_found",
            )

        normalized_task = task_type.lower() if task_type else None
        normalized_tier = tier.lower() if tier else None
        selected_ids = set(dataset_ids or [])
        extensions = self._normalize_file_extensions(file_extensions)

        datasets: list[DatasetBatchItem] = []
        for path in sorted(root_path.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in extensions:
                continue

            inferred_task, inferred_tier = self._infer_task_and_tier(path)
            if normalized_task and inferred_task != normalized_task:
                continue
            if normalized_tier and inferred_tier != normalized_tier:
                continue

            rel_no_suffix = path.relative_to(root_path).with_suffix("")
            dataset_id = rel_no_suffix.as_posix().replace("/", "__")
            if selected_ids and dataset_id not in selected_ids:
                continue

            datasets.append(
                DatasetBatchItem(
                    dataset_id=dataset_id,
                    filename=path.name,
                    file_path=str(path.resolve()),
                    task_type=inferred_task,
                    tier=inferred_tier,
                )
            )

        if limit:
            datasets = datasets[:limit]

        if not datasets:
            raise BatchValidationError(
                "No datasets matched the provided scan filters",
                code="no_datasets_matched_scan_filters",
            )

        return datasets

    def load_datasets_from_manifest(
        self, request: BatchManifestRequest
    ) -> list[DatasetBatchItem]:
        """Read dataset manifest file (JSON/CSV), apply filters, and return items."""
        manifest_path = self._resolve_manifest_path(request.manifest_path)
        if not manifest_path.exists():
            raise BatchValidationError(
                f"Manifest not found: {manifest_path}",
                code="manifest_not_found",
            )

        extension = manifest_path.suffix.lower()
        if extension == ".json":
            rows = self._load_manifest_json(manifest_path)
        elif extension == ".csv":
            rows = self._load_manifest_csv(manifest_path)
        else:
            raise BatchValidationError(
                "Manifest must be .json or .csv",
                code="invalid_manifest_extension",
            )

        datasets = [self._normalize_manifest_row(row) for row in rows]

        if request.task_type:
            task_lower = request.task_type.lower()
            datasets = [
                d
                for d in datasets
                if (d.task_type or "").lower() == task_lower
            ]

        if request.tier:
            tier_lower = request.tier.lower()
            datasets = [d for d in datasets if (d.tier or "").lower() == tier_lower]

        if request.dataset_ids:
            ids = set(request.dataset_ids)
            datasets = [d for d in datasets if d.dataset_id in ids]

        if request.limit:
            datasets = datasets[: request.limit]

        if not datasets:
            raise BatchValidationError(
                "No datasets matched the provided manifest filters",
                code="no_datasets_matched_manifest_filters",
            )

        return datasets

    def list_artifacts(self, job_id: str) -> list[str]:
        """List existing artifact files for a job."""
        return [
            str(path)
            for path in self.artifact_service.list_json_artifacts(job_id)
        ]

    async def ensure_artifact_zip(self, job_id: str, force_rebuild: bool = False) -> Optional[str]:
        """Ensure a zip package exists for the job and persist zip metadata."""
        job = await self.get_job(job_id)
        if not job:
            return None

        zip_path = self.artifact_service.package_zip(
            job_id=job_id,
            generated_at=job.get("completed_at") or job.get("created_at"),
            force_rebuild=force_rebuild,
        )
        if not zip_path:
            return None

        await self._collection().update_one(
            {"id": job_id},
            {
                "$set": {
                    "artifact_zip_path": str(zip_path),
                    "artifact_zip_ready": True,
                }
            },
        )
        return str(zip_path)

    def _resolve_manifest_path(self, manifest_path: str) -> Path:
        """Resolve manifest path from absolute or known project-relative locations."""
        path = Path(manifest_path)
        if path.is_absolute():
            return path

        if path.exists():
            return path

        candidates = [
            Path("/app") / path,
            Path(self.settings.upload_dir) / path,
            DEFAULT_DATA_DIR / path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        return path

    def _load_manifest_json(self, manifest_path: Path) -> list[dict[str, Any]]:
        """Load JSON manifest in list or {datasets:[...]} format."""
        with open(manifest_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            datasets = data.get("datasets")
            if not isinstance(datasets, list):
                raise ValueError("JSON manifest object must contain a 'datasets' list")
            return datasets

        if not isinstance(data, list):
            raise ValueError("JSON manifest must be a list or object with 'datasets'")
        return data

    def _load_manifest_csv(self, manifest_path: Path) -> list[dict[str, Any]]:
        """Load CSV manifest rows using header names as keys."""
        with open(manifest_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    def _normalize_manifest_row(self, row: dict[str, Any]) -> DatasetBatchItem:
        """Normalize a manifest row into DatasetBatchItem."""
        filename = row.get("filename") or row.get("file_name") or ""
        file_path = row.get("file_path") or row.get("path") or ""
        if not filename and file_path:
            filename = Path(file_path).name
        if not file_path:
            raise ValueError(f"Manifest row missing file_path/path: {row}")

        dataset_id = row.get("dataset_id") or row.get("id") or Path(filename).stem
        if not dataset_id:
            raise ValueError(f"Manifest row missing dataset_id/id: {row}")

        inferred_task, inferred_tier = self._infer_task_and_tier(Path(file_path))
        task_type = str(row.get("task_type")) if row.get("task_type") else inferred_task
        normalized_tier = str(row.get("tier")) if row.get("tier") else inferred_tier

        return DatasetBatchItem(
            dataset_id=str(dataset_id),
            filename=str(filename) if filename else Path(file_path).name,
            file_path=str(file_path),
            task_type=task_type,
            tier=normalized_tier,
            target_column=(
                str(row.get("target_column")) if row.get("target_column") else None
            ),
            intent=(str(row.get("intent")) if row.get("intent") else None),
        )

    def _resolve_datasets_root(self, datasets_root: Optional[str]) -> Path:
        """Resolve datasets root path from request or default upload directory."""
        if datasets_root:
            path = Path(datasets_root)
            if path.is_absolute():
                return path
            if path.exists():
                return path

            candidates = [
                Path("/app") / path,
                Path(self.settings.upload_dir) / path,
                DEFAULT_DATA_DIR / path,
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            return path

        return Path(self.settings.upload_dir) / "datasets"

    def _resolve_dataset_file_path(self, file_path: str) -> Path:
        """Resolve dataset file path from absolute or known project-relative locations."""
        path = Path(file_path)
        if path.is_absolute() or path.exists():
            return path

        candidates = [
            Path("/app") / path,
            Path(self.settings.upload_dir) / path,
            DEFAULT_DATA_DIR / path,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        return path

    def _normalize_file_extensions(self, file_extensions: list[str]) -> set[str]:
        """Normalize file extension filters to lowercase dot-prefixed values."""
        normalized: set[str] = set()
        for extension in file_extensions:
            ext = extension.strip().lower()
            if not ext:
                continue
            if not ext.startswith("."):
                ext = f".{ext}"
            normalized.add(ext)

        if not normalized:
            normalized.add(".csv")

        return normalized

    def _infer_task_and_tier(self, file_path: Path) -> tuple[Optional[str], Optional[str]]:
        """Infer task_type and tier from known folder segments in path."""
        parts = [part.lower() for part in file_path.parts]

        task_type = next(
            (part for part in parts if part in self.SUPPORTED_TASK_TYPES),
            None,
        )
        tier = next((part for part in parts if part in self.SUPPORTED_TIERS), None)
        return task_type, tier

    def _compute_signature(self, payload: dict[str, Any]) -> str:
        """Build deterministic hash for conflict/idempotency checks."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def _ensure_no_active_job_conflict(
        self,
        source_filter: dict[str, Any],
        message: str,
        code: str,
    ) -> None:
        """Prevent launching duplicate active jobs for the same source signature."""
        query = {
            "status": {
                "$in": [
                    BatchJobStatus.QUEUED.value,
                    BatchJobStatus.PROCESSING.value,
                ]
            }
        }
        query.update(source_filter)

        existing_job = await self._collection().find_one(query)
        if existing_job:
            raise BatchConflictError(
                message,
                code=code,
                details={"existing_job_id": existing_job.get("id")},
            )

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get raw job document by ID."""
        doc = await self._collection().find_one({"id": job_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return doc

    async def get_monitoring_report(self, job_id: Optional[str] = None) -> Dict[str, Any]:
        """Build monitoring payload for one job or all active jobs."""
        now = datetime.now(timezone.utc)

        if job_id:
            job = await self.get_job(job_id)
            if not job:
                raise BatchValidationError(
                    f"Batch job {job_id} not found",
                    code="batch_job_not_found",
                )
            return {
                "generated_at": now,
                "queue_depth": self._queue.qsize(),
                "job": self._build_job_monitoring_summary(job),
            }

        active_jobs_cursor = self._collection().find(
            {
                "status": {
                    "$in": [
                        BatchJobStatus.QUEUED.value,
                        BatchJobStatus.PROCESSING.value,
                    ]
                }
            }
        )
        active_jobs = []
        async for job in active_jobs_cursor:
            job.pop("_id", None)
            active_jobs.append(self._build_job_monitoring_summary(job))

        completed_jobs_count = await self._collection().count_documents(
            {"status": BatchJobStatus.COMPLETED.value}
        )
        failed_jobs_count = await self._collection().count_documents(
            {"status": BatchJobStatus.FAILED.value}
        )

        return {
            "generated_at": now,
            "queue_depth": self._queue.qsize(),
            "active_jobs": active_jobs,
            "active_job_count": len(active_jobs),
            "completed_job_count": completed_jobs_count,
            "failed_job_count": failed_jobs_count,
        }

    def _build_job_monitoring_summary(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize one job into monitoring summary output."""
        return {
            "batch_job_id": job.get("id"),
            "status": job.get("status"),
            "created_at": job.get("created_at"),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
            "progress": job.get("progress", {}),
            "source": job.get("source", {}),
            "audit": job.get("audit", {}),
            "metrics": job.get("metrics", {}),
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Request cancellation for a running/queued job."""
        result = await self._collection().update_one(
            {"id": job_id}, {"$set": {"cancel_requested": True}}
        )
        if result.matched_count == 0:
            return False

        logger.info("Batch cancellation requested", job_id=job_id)
        return True

    async def _worker_loop(self, worker_index: int) -> None:
        """Main worker loop."""
        logger.info("Batch worker started", worker=worker_index)
        while self._running:
            has_item = False
            try:
                job_id = await self._queue.get()
                has_item = True
                await self._process_job(job_id)
            except asyncio.CancelledError:
                logger.info("Batch worker cancelled", worker=worker_index)
                raise
            except Exception as exc:
                logger.error(
                    "Unhandled batch worker error",
                    worker=worker_index,
                    error=str(exc),
                )
            finally:
                if has_item:
                    self._queue.task_done()

        logger.info("Batch worker stopped", worker=worker_index)

    async def _process_job(self, job_id: str) -> None:
        """Process all items in a job sequentially."""
        job = await self.get_job(job_id)
        if not job:
            return

        if job.get("status") in {
            BatchJobStatus.CANCELLED.value,
            BatchJobStatus.COMPLETED.value,
        }:
            return

        now = datetime.now(timezone.utc)
        await self._collection().update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": BatchJobStatus.PROCESSING.value,
                    "started_at": now,
                }
            },
        )

        job = await self.get_job(job_id)
        if not job:
            return

        fail_fast = job["settings"].get("fail_fast", False)
        max_retries = job["settings"].get(
            "max_retries", self.settings.batch_item_max_retries
        )
        create_sessions = job["settings"].get("create_sessions", True)

        for idx, item in enumerate(job["items"]):
            job = await self.get_job(job_id)
            if not job:
                return

            if job.get("cancel_requested"):
                await self._mark_remaining_as_skipped(job_id)
                await self._finish_job(job_id, BatchJobStatus.CANCELLED.value)
                return

            if item.get("status") not in {
                BatchItemStatus.PENDING.value,
                BatchItemStatus.FAILED.value,
            }:
                continue

            try:
                await self._set_item_status(
                    job_id,
                    idx,
                    status=BatchItemStatus.RUNNING.value,
                    started_at=datetime.now(timezone.utc),
                    error=None,
                )

                item_start = datetime.now(timezone.utc)
                result = await self._process_item(
                    job_id=job_id,
                    item=item,
                    max_retries=max_retries,
                    create_sessions=create_sessions,
                )
                duration = (datetime.now(timezone.utc) - item_start).total_seconds()

                await self._set_item_status(
                    job_id,
                    idx,
                    status=BatchItemStatus.SUCCEEDED.value,
                    completed_at=datetime.now(timezone.utc),
                    duration_seconds=duration,
                    session_id=result.get("session_id"),
                    artifact_path=result.get("artifact_path"),
                    orchestration=result.get("orchestration"),
                    retries=result.get("retries", 0),
                )

            except Exception as exc:
                await self._set_item_status(
                    job_id,
                    idx,
                    status=BatchItemStatus.FAILED.value,
                    completed_at=datetime.now(timezone.utc),
                    error=str(exc),
                    retries=item.get("retries", 0),
                )
                logger.error(
                    "Batch item failed",
                    job_id=job_id,
                    dataset_id=item.get("dataset_id"),
                    error=str(exc),
                )

                if fail_fast:
                    await self._mark_remaining_as_skipped(job_id)
                    await self._finish_job(job_id, BatchJobStatus.FAILED.value)
                    return

            await self._refresh_progress(job_id)

        await self._refresh_progress(job_id)
        final_status = await self._compute_final_status(job_id)
        await self._finish_job(job_id, final_status)

    async def _process_item(
        self,
        job_id: str,
        item: Dict[str, Any],
        max_retries: int,
        create_sessions: bool,
    ) -> Dict[str, Any]:
        """Run hidden agent pipeline for one dataset item with retries."""
        retries = 0
        last_error: Optional[Exception] = None

        while retries <= max_retries:
            try:
                session_id = None
                conversation_history = []

                if create_sessions:
                    session = await self.session_manager.create_session(
                        title=f"Batch {job_id} - {item.get('filename', 'dataset')}"
                    )
                    session_id = session.id

                user_message = self._build_batch_user_message(item)
                file_context = (
                    f"\n\n[File attached: {item['filename']} (0 MB) at path: {item['file_path']}]"
                )
                user_message_with_context = user_message + file_context

                if session_id:
                    await self.session_manager.add_message(
                        session_id=session_id,
                        role="user",
                        content=user_message,
                        metadata={
                            "attached_file": {
                                "filename": item["filename"],
                                "path": item["file_path"],
                                "size_mb": 0,
                            }
                        },
                    )

                pipeline_service = AgentPipelineService(
                    self.llm_service,
                    self.agent_registry,
                    self.mcp_server_service,
                )

                assistant_content, orchestration_data = (
                    await pipeline_service.process_with_pipeline(
                        user_message=user_message_with_context,
                        conversation_history=conversation_history,
                    )
                )

                if not orchestration_data or "orchestration" not in orchestration_data:
                    raise RuntimeError(
                        f"Pipeline generation failed: {assistant_content[:200]}"
                    )

                orchestration = orchestration_data["orchestration"]
                validation = orchestration.get("validation", {})
                if validation.get("status") != "valid":
                    issues = validation.get("issues", [])
                    issue_preview = (
                        "; ".join(str(issue.get("code")) for issue in issues[:5])
                        if isinstance(issues, list)
                        else "unknown_validation_issue"
                    )
                    raise RuntimeError(
                        "Orchestration validation failed; refusing to save uncertain batch artifact: "
                        f"{issue_preview}"
                    )

                artifact_path = self._save_artifact(job_id, item, orchestration)

                if session_id:
                    await self.session_manager.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=assistant_content,
                        metadata={
                            "orchestration": orchestration_data,
                            "agents_used": [
                                "interaction_agent",
                                "planner_agent",
                                "orchestrator_agent",
                            ],
                            "batch_job_id": job_id,
                        },
                    )

                return {
                    "session_id": session_id,
                    "artifact_path": artifact_path,
                    "orchestration": orchestration,
                    "retries": retries,
                }

            except Exception as exc:
                last_error = exc
                retries += 1
                if retries > max_retries:
                    break

                await asyncio.sleep(self.settings.batch_retry_delay_seconds * retries)

        raise RuntimeError(f"Max retries exceeded: {last_error}")

    def _build_batch_user_message(self, item: Dict[str, Any]) -> str:
        """Create deterministic message for non-interactive pipeline generation."""
        if item.get("intent"):
            return item["intent"]

        task_type = str(item.get("task_type") or "").strip().lower()
        if task_type == "classification":
            return "Build a classification model for this dataset"
        if task_type == "regression":
            return "Build a regression model for this dataset"

        return "Build a machine learning model for this dataset"

    def _save_artifact(
        self, job_id: str, item: Dict[str, Any], orchestration: Dict[str, Any]
    ) -> str:
        """Persist orchestration JSON artifact for downstream Sim usage."""
        output_dir = Path(self.settings.batch_artifacts_dir) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_dataset = item["dataset_id"].replace("/", "_")
        artifact_path = output_dir / f"{safe_dataset}.json"

        payload = {
            "dataset_id": item["dataset_id"],
            "filename": item["filename"],
            "file_path": item["file_path"],
            "task_type": item.get("task_type"),
            "tier": item.get("tier"),
            "target_column": item.get("target_column"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "workflow": orchestration,
        }

        with open(artifact_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

        return str(artifact_path)

    async def _set_item_status(
        self,
        job_id: str,
        index: int,
        **fields,
    ) -> None:
        """Update one item fields in-place using positional path."""
        update_doc = {f"items.{index}.{key}": value for key, value in fields.items()}
        await self._collection().update_one({"id": job_id}, {"$set": update_doc})

    async def _refresh_progress(self, job_id: str) -> None:
        """Recompute and persist progress counters."""
        job = await self.get_job(job_id)
        if not job:
            return

        total = len(job["items"])
        succeeded = sum(1 for i in job["items"] if i["status"] == BatchItemStatus.SUCCEEDED.value)
        failed = sum(1 for i in job["items"] if i["status"] == BatchItemStatus.FAILED.value)
        skipped = sum(1 for i in job["items"] if i["status"] == BatchItemStatus.SKIPPED.value)
        processed = succeeded + failed + skipped

        durations = [
            float(item["duration_seconds"])
            for item in job["items"]
            if item.get("duration_seconds") is not None
        ]
        total_duration = sum(durations)
        avg_duration = (total_duration / len(durations)) if durations else None
        max_duration = max(durations) if durations else None
        total_retries = sum(int(item.get("retries", 0)) for item in job["items"])

        failure_reason_buckets: dict[str, int] = {}
        for item in job["items"]:
            if item.get("status") != BatchItemStatus.FAILED.value:
                continue
            error_text = (item.get("error") or "unknown_error").strip().split("\n")[0]
            bucket = error_text[:120] if error_text else "unknown_error"
            failure_reason_buckets[bucket] = failure_reason_buckets.get(bucket, 0) + 1

        job_queue_wait_seconds = None
        if job.get("created_at") and job.get("started_at"):
            job_queue_wait_seconds = (
                job["started_at"] - job["created_at"]
            ).total_seconds()

        await self._collection().update_one(
            {"id": job_id},
            {
                "$set": {
                    "progress": {
                        "total": total,
                        "processed": processed,
                        "succeeded": succeeded,
                        "failed": failed,
                        "skipped": skipped,
                    },
                    "metrics": {
                        "queue_depth_at_submit": job.get("metrics", {}).get(
                            "queue_depth_at_submit", 0
                        ),
                        "job_queue_wait_seconds": job_queue_wait_seconds,
                        "total_retries": total_retries,
                        "items_with_duration": len(durations),
                        "total_item_duration_seconds": total_duration,
                        "avg_item_duration_seconds": avg_duration,
                        "max_item_duration_seconds": max_duration,
                        "failure_reason_buckets": failure_reason_buckets,
                        "last_updated_at": datetime.now(timezone.utc),
                    },
                }
            },
        )

    async def _mark_remaining_as_skipped(self, job_id: str) -> None:
        """Mark pending/running items as skipped during cancellation/fail-fast."""
        job = await self.get_job(job_id)
        if not job:
            return

        now = datetime.now(timezone.utc)
        for index, item in enumerate(job["items"]):
            if item["status"] in {
                BatchItemStatus.PENDING.value,
                BatchItemStatus.RUNNING.value,
            }:
                await self._set_item_status(
                    job_id,
                    index,
                    status=BatchItemStatus.SKIPPED.value,
                    completed_at=now,
                )

        await self._refresh_progress(job_id)

    async def _compute_final_status(self, job_id: str) -> str:
        """Determine final job status from item outcomes."""
        job = await self.get_job(job_id)
        if not job:
            return BatchJobStatus.FAILED.value

        if job.get("cancel_requested"):
            return BatchJobStatus.CANCELLED.value

        progress = job.get("progress", {})
        succeeded = progress.get("succeeded", 0)
        failed = progress.get("failed", 0)

        if succeeded > 0 and failed == 0:
            return BatchJobStatus.COMPLETED.value
        if succeeded > 0 and failed > 0:
            return BatchJobStatus.COMPLETED.value
        return BatchJobStatus.FAILED.value

    async def _finish_job(self, job_id: str, status: str) -> None:
        """Finalize job status and completion timestamp."""
        completed_at = datetime.now(timezone.utc)
        await self._collection().update_one(
            {"id": job_id},
            {
                "$set": {
                    "status": status,
                    "completed_at": completed_at,
                }
            },
        )

        if self.settings.batch_auto_zip_on_completion:
            await self.ensure_artifact_zip(job_id)

        logger.info("Batch job finished", job_id=job_id, status=status)
