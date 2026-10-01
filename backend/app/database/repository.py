from __future__ import annotations

from threading import Lock
from uuid import uuid4

from backend.app.models.inspection import Inspection


class InspectionRepository:
    def __init__(self):
        self._store: dict[str, Inspection] = {}
        self._lock = Lock()

    def create(self, inspection: Inspection) -> Inspection:
        with self._lock:
            if inspection.inspection_id in self._store:
                raise ValueError(f"Inspection already exists: {inspection.inspection_id}")
            self._store[inspection.inspection_id] = inspection
            return inspection

    def list(self) -> list[Inspection]:
        with self._lock:
            return list(self._store.values())

    def get(self, inspection_id: str) -> Inspection | None:
        with self._lock:
            return self._store.get(inspection_id)

    def update(self, inspection: Inspection) -> Inspection:
        with self._lock:
            self._store[inspection.inspection_id] = inspection
            return inspection

    def generate_id(self) -> str:
        return f"INS-{uuid4().hex[:8].upper()}"
