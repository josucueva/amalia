"""
Batch job models for unattended pipeline generation and export.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


TASK_FILTER_DESCRIPTION = "Optional task filter (classification/regression)"
TIER_FILTER_DESCRIPTION = "Optional tier filter"
DATASET_ALLOW_LIST_DESCRIPTION = "Optional dataset ID allow-list"
LIMIT_DESCRIPTION = "Optional max number of datasets to include"


class BatchJobStatus(str, Enum):
    """Lifecycle status of a batch job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchItemStatus(str, Enum):
    """Status for an individual dataset item inside a batch."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class DatasetBatchItem(BaseModel):
    """Input specification for a dataset to process."""

    dataset_id: str = Field(..., description="Unique dataset identifier")
    filename: str = Field(..., description="Dataset file name")
    file_path: str = Field(..., description="Absolute/accessible path to dataset")
    task_type: Optional[str] = Field(
        default=None,
        description="Task type hint (classification/regression)",
    )
    tier: Optional[str] = Field(default=None, description="Difficulty tier hint")
    target_column: Optional[str] = Field(
        default=None,
        description="Target column hint for supervised tasks",
    )
    intent: Optional[str] = Field(
        default=None,
        description="Optional explicit user intent override",
    )


class BatchProcessSettings(BaseModel):
    """Per-job processing controls."""

    max_retries: int = Field(default=2, ge=0, le=5)
    fail_fast: bool = Field(default=False)
    create_sessions: bool = Field(default=True)


class BatchProcessRequest(BaseModel):
    """Request to start a batch pipeline generation job."""

    datasets: List[DatasetBatchItem] = Field(..., min_length=1)
    tags: Optional[List[str]] = Field(default=None)
    settings: BatchProcessSettings = Field(default_factory=BatchProcessSettings)


class BatchManifestRequest(BaseModel):
    """Request to start a batch job from a JSON/CSV manifest file."""

    manifest_path: str = Field(..., description="Path to dataset manifest file")
    task_type: Optional[str] = Field(
        default=None,
        description=TASK_FILTER_DESCRIPTION,
    )
    tier: Optional[str] = Field(default=None, description=TIER_FILTER_DESCRIPTION)
    dataset_ids: Optional[List[str]] = Field(
        default=None,
        description=DATASET_ALLOW_LIST_DESCRIPTION,
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description=LIMIT_DESCRIPTION,
    )
    tags: Optional[List[str]] = Field(default=None)
    settings: BatchProcessSettings = Field(default_factory=BatchProcessSettings)


class BatchScanRequest(BaseModel):
    """Request to scan dataset directories and submit a batch job directly."""

    datasets_root: Optional[str] = Field(
        default=None,
        description="Root folder containing datasets tree",
    )
    task_type: Optional[str] = Field(
        default=None,
        description=TASK_FILTER_DESCRIPTION,
    )
    tier: Optional[str] = Field(default=None, description=TIER_FILTER_DESCRIPTION)
    dataset_ids: Optional[List[str]] = Field(
        default=None,
        description=DATASET_ALLOW_LIST_DESCRIPTION,
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description=LIMIT_DESCRIPTION,
    )
    file_extensions: List[str] = Field(
        default_factory=lambda: [".csv"],
        description="Dataset file extensions to include",
    )
    tags: Optional[List[str]] = Field(default=None)
    settings: BatchProcessSettings = Field(default_factory=BatchProcessSettings)


class BatchGenerateManifestRequest(BaseModel):
    """Request to generate a JSON manifest by scanning dataset directories."""

    datasets_root: Optional[str] = Field(
        default=None,
        description="Root folder containing datasets tree",
    )
    output_path: Optional[str] = Field(
        default=None,
        description="Optional output path for generated JSON manifest",
    )
    task_type: Optional[str] = Field(
        default=None,
        description=TASK_FILTER_DESCRIPTION,
    )
    tier: Optional[str] = Field(default=None, description=TIER_FILTER_DESCRIPTION)
    dataset_ids: Optional[List[str]] = Field(
        default=None,
        description=DATASET_ALLOW_LIST_DESCRIPTION,
    )
    limit: Optional[int] = Field(
        default=None,
        ge=1,
        description=LIMIT_DESCRIPTION,
    )
    file_extensions: List[str] = Field(
        default_factory=lambda: [".csv"],
        description="Dataset file extensions to include",
    )


class ManifestValidationIssue(BaseModel):
    """Validation issue for a manifest row."""

    row_index: int
    dataset_id: Optional[str] = None
    error: str


class BatchValidateManifestRequest(BaseModel):
    """Request to validate manifest structure and referenced files."""

    manifest_path: str = Field(..., description="Path to dataset manifest file")


class BatchGenerateManifestResponse(BaseModel):
    """Response payload for generated manifest."""

    manifest_path: str
    total_datasets: int
    datasets: List[DatasetBatchItem]


class BatchValidateManifestResponse(BaseModel):
    """Response payload for manifest validation."""

    manifest_path: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    issues: List[ManifestValidationIssue]


class BatchRerunFailedRequest(BaseModel):
    """Request to rerun failed items from an existing batch job."""

    include_skipped: bool = Field(default=False)
    limit: Optional[int] = Field(default=None, ge=1)
    tags: Optional[List[str]] = Field(default=None)
    settings: Optional[BatchProcessSettings] = Field(default=None)


class BatchSubmitResponse(BaseModel):
    """Immediate response when a job is queued."""

    batch_job_id: str
    status: BatchJobStatus
    total_datasets: int
    created_at: datetime


class BatchJobProgress(BaseModel):
    """Progress counters for a batch job."""

    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0


class BatchJobItemResult(BaseModel):
    """Execution/result state for a single dataset."""

    dataset_id: str
    filename: str
    file_path: str
    task_type: Optional[str] = None
    tier: Optional[str] = None
    target_column: Optional[str] = None
    status: BatchItemStatus = BatchItemStatus.PENDING
    retries: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    session_id: Optional[str] = None
    artifact_path: Optional[str] = None
    orchestration: Optional[Dict[str, Any]] = None


class BatchJobStatusResponse(BaseModel):
    """Status response for batch polling."""

    batch_job_id: str
    status: BatchJobStatus
    progress: BatchJobProgress
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancel_requested: bool = False
    tags: Optional[List[str]] = None
    artifact_zip_ready: bool = False
    artifact_zip_path: Optional[str] = None
    artifact_zip_download_url: Optional[str] = None


class BatchJobResultsResponse(BaseModel):
    """Detailed results payload for a completed/in-progress batch."""

    batch_job_id: str
    status: BatchJobStatus
    progress: BatchJobProgress
    results: List[BatchJobItemResult]
    artifact_zip_ready: bool = False
    artifact_zip_path: Optional[str] = None
    artifact_zip_download_url: Optional[str] = None


class BatchArtifactListResponse(BaseModel):
    """Artifact metadata for a batch job."""

    batch_job_id: str
    artifact_count: int
    artifacts: List[str]
