from datetime import datetime, timezone
import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.batch import router as batch_router
from app.services.batch_processor import BatchConflictError, BatchValidationError


class FakeBatchProcessor:
    def __init__(self):
        self.raise_error = None
        self.last_call = None
        self.idempotency_calls = []
        self.audit_calls = []

    async def submit_job_idempotent(
        self,
        idempotency_key,
        scope,
        request_payload,
        submit_operation,
    ):
        self.last_call = (
            "submit_job_idempotent",
            {
                "idempotency_key": idempotency_key,
                "scope": scope,
                "request_payload": request_payload,
            },
        )
        self.idempotency_calls.append(self.last_call[1])
        if self.raise_error:
            raise self.raise_error
        return await submit_operation()

    async def record_submission_audit(
        self,
        job_id,
        *,
        idempotency_key,
        scope,
        replayed,
    ):
        await asyncio.sleep(0)
        self.audit_calls.append(
            {
                "job_id": job_id,
                "idempotency_key": idempotency_key,
                "scope": scope,
                "replayed": replayed,
            }
        )

    async def get_monitoring_report(self, job_id=None):
        await asyncio.sleep(0)
        if self.raise_error:
            raise self.raise_error
        if job_id:
            return {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "queue_depth": 0,
                "job": {
                    "batch_job_id": job_id,
                    "status": "processing",
                    "metrics": {
                        "avg_item_duration_seconds": 4.5,
                        "total_retries": 2,
                        "failure_reason_buckets": {"Timeout": 1},
                    },
                },
            }

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "queue_depth": 1,
            "active_jobs": [
                {
                    "batch_job_id": "batch_active_001",
                    "status": "processing",
                }
            ],
            "active_job_count": 1,
            "completed_job_count": 5,
            "failed_job_count": 1,
        }

    async def submit_job_from_scan(self, request_data):
        await asyncio.sleep(0)
        self.last_call = ("submit_job_from_scan", request_data)
        if self.raise_error:
            raise self.raise_error
        return {
            "id": "batch_scan_123",
            "status": "queued",
            "items": [{"dataset_id": "ds_1"}, {"dataset_id": "ds_2"}],
            "created_at": datetime.now(timezone.utc),
        }

    def generate_manifest_from_scan(self, request_data):
        self.last_call = ("generate_manifest_from_scan", request_data)
        if self.raise_error:
            raise self.raise_error
        return {
            "manifest_path": "/tmp/generated_manifest.json",
            "datasets": [
                {
                    "dataset_id": "classification__easy__iris",
                    "filename": "iris.csv",
                    "file_path": "/data/uploads/datasets/classification/easy/iris.csv",
                    "task_type": "classification",
                    "tier": "easy",
                    "target_column": None,
                    "intent": None,
                }
            ],
        }

    def validate_manifest(self, request_data):
        self.last_call = ("validate_manifest", request_data)
        if self.raise_error:
            raise self.raise_error
        return {
            "manifest_path": request_data.manifest_path,
            "total_rows": 3,
            "valid_rows": 2,
            "invalid_rows": 1,
            "issues": [
                {
                    "row_index": 2,
                    "dataset_id": "broken_ds",
                    "error": "Dataset file not found: /missing.csv",
                }
            ],
        }

    async def submit_rerun_failed_job(
        self,
        source_job_id,
        include_skipped=False,
        limit=None,
        tags=None,
        settings=None,
    ):
        await asyncio.sleep(0)
        self.last_call = (
            "submit_rerun_failed_job",
            {
                "source_job_id": source_job_id,
                "include_skipped": include_skipped,
                "limit": limit,
                "tags": tags,
                "settings": settings,
            },
        )
        if self.raise_error:
            raise self.raise_error
        return {
            "id": "batch_rerun_123",
            "status": "queued",
            "items": [{"dataset_id": "ds_failed_1"}],
            "created_at": datetime.now(timezone.utc),
        }


class AppState:
    def __init__(self, processor):
        self.batch_processor = processor


def build_client(processor: FakeBatchProcessor) -> TestClient:
    app = FastAPI()
    app.include_router(batch_router)
    app.state = AppState(processor)
    return TestClient(app)


def test_scan_and_launch_returns_submit_response():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.post(
        "/api/batch/scan-and-launch",
        json={
            "datasets_root": "/data/uploads/datasets",
            "task_type": "classification",
            "tier": "easy",
            "file_extensions": [".csv"],
            "settings": {
                "max_retries": 1,
                "fail_fast": False,
                "create_sessions": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_job_id"] == "batch_scan_123"
    assert payload["status"] == "queued"
    assert payload["total_datasets"] == 2
    assert processor.audit_calls[0]["scope"] == "scan-and-launch"


def test_generate_manifest_returns_manifest_payload():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.post(
        "/api/batch/generate-manifest",
        json={
            "datasets_root": "/data/uploads/datasets",
            "task_type": "classification",
            "tier": "easy",
            "file_extensions": [".csv"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["manifest_path"] == "/tmp/generated_manifest.json"
    assert payload["total_datasets"] == 1
    assert payload["datasets"][0]["dataset_id"] == "classification__easy__iris"


def test_validate_manifest_returns_issue_breakdown():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.post(
        "/api/batch/validate-manifest",
        json={"manifest_path": "/tmp/manifest.json"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["manifest_path"] == "/tmp/manifest.json"
    assert payload["total_rows"] == 3
    assert payload["valid_rows"] == 2
    assert payload["invalid_rows"] == 1
    assert payload["issues"][0]["dataset_id"] == "broken_ds"


def test_rerun_failed_returns_submit_response():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.post(
        "/api/batch/batch_001/rerun-failed",
        json={
            "include_skipped": False,
            "limit": 10,
            "tags": ["retry"],
            "settings": {
                "max_retries": 2,
                "fail_fast": False,
                "create_sessions": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["batch_job_id"] == "batch_rerun_123"
    assert payload["status"] == "queued"
    assert payload["total_datasets"] == 1
    assert processor.audit_calls[0]["scope"].startswith("rerun-failed:")


def test_scan_and_launch_maps_validation_error_to_400():
    processor = FakeBatchProcessor()
    processor.raise_error = ValueError("No datasets matched the provided scan filters")
    client = build_client(processor)

    response = client.post(
        "/api/batch/scan-and-launch",
        json={
            "datasets_root": "/data/uploads/datasets",
            "file_extensions": [".csv"],
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["category"] == "validation"
    assert "No datasets matched" in detail["message"]


def test_generate_manifest_maps_file_not_found_to_400():
    processor = FakeBatchProcessor()
    processor.raise_error = FileNotFoundError("Datasets root not found")
    client = build_client(processor)

    response = client.post(
        "/api/batch/generate-manifest",
        json={
            "datasets_root": "/missing/path",
            "file_extensions": [".csv"],
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["category"] == "validation"
    assert "Datasets root not found" in detail["message"]


def test_validate_manifest_maps_invalid_request_to_400():
    processor = FakeBatchProcessor()
    processor.raise_error = ValueError("Manifest must be .json or .csv")
    client = build_client(processor)

    response = client.post(
        "/api/batch/validate-manifest",
        json={"manifest_path": "/tmp/manifest.txt"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["category"] == "validation"
    assert "Manifest must be .json or .csv" in detail["message"]


def test_rerun_failed_maps_missing_job_to_400():
    processor = FakeBatchProcessor()
    processor.raise_error = BatchValidationError(
        "Batch job batch_missing not found",
        code="source_batch_not_found",
    )
    client = build_client(processor)

    response = client.post(
        "/api/batch/batch_missing/rerun-failed",
        json={},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "source_batch_not_found"
    assert detail["category"] == "validation"


def test_scan_and_launch_with_idempotency_header_uses_scope():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.post(
        "/api/batch/scan-and-launch",
        headers={"Idempotency-Key": "scan-001"},
        json={
            "datasets_root": "/data/uploads/datasets",
            "file_extensions": [".csv"],
            "settings": {
                "max_retries": 1,
                "fail_fast": False,
                "create_sessions": True,
            },
        },
    )

    assert response.status_code == 200
    assert processor.idempotency_calls[0]["scope"] == "scan-and-launch"
    assert processor.idempotency_calls[0]["idempotency_key"] == "scan-001"
    assert processor.audit_calls[0]["idempotency_key"] == "scan-001"


def test_scan_and_launch_maps_conflict_error_to_409():
    processor = FakeBatchProcessor()
    processor.raise_error = BatchConflictError(
        "An equivalent scan-and-launch batch is already active",
        code="scan_batch_already_active",
    )
    client = build_client(processor)

    response = client.post(
        "/api/batch/scan-and-launch",
        json={
            "datasets_root": "/data/uploads/datasets",
            "file_extensions": [".csv"],
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "scan_batch_already_active"
    assert detail["category"] == "concurrency"


def test_monitoring_report_returns_aggregate_payload():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.get("/api/batch/monitoring/report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["queue_depth"] == 1
    assert payload["active_job_count"] == 1
    assert payload["completed_job_count"] == 5


def test_monitoring_report_for_job_returns_metrics():
    processor = FakeBatchProcessor()
    client = build_client(processor)

    response = client.get("/api/batch/batch_001/monitoring")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["batch_job_id"] == "batch_001"
    assert payload["job"]["metrics"]["total_retries"] == 2
