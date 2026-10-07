from __future__ import annotations

import re
from pathlib import Path


class LocalStorage:
    def __init__(self, root_dir: str = "uploads"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_component(value: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "")
        safe = safe.strip("._")
        return safe or "inspection"

    @staticmethod
    def _safe_filename(filename: str) -> str:
        name = Path(filename).name
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "upload")
        return safe.strip("._") or "upload.bin"

    def inspection_root(self, inspection_id: str) -> Path:
        safe_inspection_id = self._safe_component(inspection_id)
        folder = self.root_dir / "inspections" / safe_inspection_id
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def save(self, inspection_id: str, filename: str, content: bytes) -> str:
        folder = self.inspection_root(inspection_id)
        safe_name = self._safe_filename(filename)
        destination = folder / safe_name
        destination.write_bytes(content)
        return str(destination)

    def resolve(self, inspection_id: str, stored_filename: str) -> Path:
        folder = self.inspection_root(inspection_id)
        safe_name = self._safe_filename(stored_filename)
        target = (folder / safe_name).resolve()
        base = folder.resolve()
        if not target.is_relative_to(base):
            raise ValueError("Path traversal detected")
        return target
