"""StorageService — local filesystem implementation.

Interface is deliberately thin so swapping to S3 later only requires
writing a new class that satisfies the same three public methods:
  save(file) -> str        # returns relative URL path
  delete(url_path) -> None
  public_url(url_path) -> str

The upload directory is created automatically on first use.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings

settings = get_settings()

# Allowed MIME types → expected file extensions
_ALLOWED: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png":  ".png",
    "image/webp": ".webp",
}

_MAX_BYTES = settings.max_upload_size_mb * 1024 * 1024


class LocalStorageService:
    """Store uploaded images on the local filesystem under `upload_dir`."""

    def __init__(self, upload_dir: str | None = None) -> None:
        self._base = Path(upload_dir or settings.upload_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────────

    async def save(self, file: UploadFile) -> str:
        """Validate, persist, and return the relative URL path (e.g. /uploads/abc.jpg).

        Raises HTTP 400 on invalid type or oversized file.
        """
        self._validate_content_type(file.content_type)
        contents = await file.read()
        self._validate_size(len(contents))

        ext = _ALLOWED[file.content_type]  # type: ignore[index]
        filename = f"{uuid.uuid4().hex}{ext}"
        dest = self._base / filename
        dest.write_bytes(contents)

        return f"/uploads/{filename}"

    def delete(self, url_path: str) -> None:
        """Remove a stored file if it exists.  Silently ignores missing files."""
        filename = url_path.lstrip("/").removeprefix("uploads/")
        target = self._base / filename
        target.unlink(missing_ok=True)

    def public_url(self, url_path: str) -> str:
        """Return the public URL path as-is (same-origin serving via FastAPI mount)."""
        return url_path

    # ── Validation helpers ────────────────────────────────────────────────────

    @staticmethod
    def _validate_content_type(content_type: str | None) -> None:
        if content_type not in _ALLOWED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipe file tidak didukung. Gunakan: {', '.join(_ALLOWED)}.",
            )

    @staticmethod
    def _validate_size(num_bytes: int) -> None:
        if num_bytes > _MAX_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ukuran file melebihi batas {settings.max_upload_size_mb} MB.",
            )


# Module-level singleton — imported by routers/services
storage = LocalStorageService()
