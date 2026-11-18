"""Print field evidence confidence and match status for sample invoice files."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from docextract.core.config import get_settings
from docextract.services.evidence.pipeline import extract_evidence_document

_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}


async def _inspect(path: Path) -> dict[str, object]:
    mime_type = _MIME_TYPES[path.suffix.lower()]
    try:
        result = await extract_evidence_document(
            path.read_bytes(), mime_type, path.name, get_settings()
        )
    except Exception as error:
        return {"file": path.name, "error": type(error).__name__}
    return {
        "file": path.name,
        "fields": {
            name: {
                "confidence": field.confidence,
                "status": field.source.status,
                "match_count": field.source.match_count,
                "reason": field.source.reason,
            }
            for name, field in result.fields.items()
        },
    }


async def _run(folder: Path) -> None:
    paths = sorted(
        path for path in folder.iterdir() if path.is_file() and path.suffix.lower() in _MIME_TYPES
    )
    for path in paths:
        print(json.dumps(await _inspect(path), ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Report per-field confidence and evidence matching for sample documents."
    )
    parser.add_argument("folder", type=Path, help="Folder containing PDF/image samples")
    args = parser.parse_args()
    if not args.folder.is_dir():
        parser.error("folder must be an existing directory")
    asyncio.run(_run(args.folder))


if __name__ == "__main__":
    main()
