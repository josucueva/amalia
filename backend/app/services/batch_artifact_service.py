"""
Artifact packaging service for batch pipeline outputs.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Optional


class BatchArtifactService:
    """Handles artifact listing and zip package generation for batch jobs."""

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)

    def artifacts_dir(self, job_id: str) -> Path:
        """Return artifact directory for a job."""
        return self.base_dir / job_id

    def zip_path(self, job_id: str) -> Path:
        """Return zip package path for a job."""
        return self.artifacts_dir(job_id) / f"{job_id}_artifacts.zip"

    def list_json_artifacts(self, job_id: str) -> list[Path]:
        """List JSON artifact files for a job."""
        artifacts_dir = self.artifacts_dir(job_id)
        if not artifacts_dir.exists():
            return []

        return sorted(
            path
            for path in artifacts_dir.glob("*.json")
            if path.is_file() and not path.name.endswith("_artifacts.zip")
        )

    def package_zip(
        self,
        job_id: str,
        generated_at: Any,
        force_rebuild: bool = False,
    ) -> Optional[Path]:
        """Create (or reuse) a zip package for job artifacts."""
        artifact_files = self.list_json_artifacts(job_id)
        if not artifact_files:
            return None

        output_path = self.zip_path(job_id)
        if output_path.exists() and not force_rebuild:
            return output_path

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for artifact in artifact_files:
                zf.write(artifact, arcname=artifact.name)

            manifest = {
                "batch_job_id": job_id,
                "generated_at": generated_at,
                "artifact_count": len(artifact_files),
                "artifacts": [artifact.name for artifact in artifact_files],
            }
            zf.writestr("manifest.json", json.dumps(manifest, default=str, indent=2))

        return output_path
