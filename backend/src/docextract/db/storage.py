"""Day-partitioned local document storage."""

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/tiff": ".tiff",
}


def store_document(
    storage_root: Path,
    file_id: UUID,
    content_type: str,
    uploaded_at: datetime,
    content: bytes,
) -> str:
    """Atomically store a document under its UTC upload date and return a relative path."""
    extension = _EXTENSIONS.get(content_type)
    if extension is None:
        raise ValueError("Unsupported document content type")
    utc_date = uploaded_at.astimezone(UTC).date()
    relative_path = Path(f"{utc_date:%Y/%m/%d}") / f"{file_id}{extension}"
    target = storage_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.tmp")
    try:
        with temporary.open("xb") as stored_file:
            stored_file.write(content)
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return relative_path.as_posix()


def delete_stored_document(storage_root: Path, relative_path: str) -> None:
    """Remove a just-written document after its database transaction fails."""
    root = storage_root.resolve()
    target = (root / relative_path).resolve()
    if not target.is_relative_to(root):
        raise ValueError("Document path escapes configured storage directory")
    target.unlink(missing_ok=True)
