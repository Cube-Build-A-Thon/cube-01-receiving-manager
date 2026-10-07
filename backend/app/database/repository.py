from __future__ import annotations

from uuid import uuid4

from sqlalchemy import JSON, String, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.models.inspection import Inspection


class Base(DeclarativeBase):
    pass


class InspectionRow(Base):
    __tablename__ = "inspections"

    org_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    inspection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


def _create_engine():
    database_url = get_settings().database_url
    engine_options = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        if database_url.endswith(":memory:"):
            engine_options["poolclass"] = StaticPool
    return create_engine(database_url, **engine_options)


class InspectionRepository:
    def __init__(self):
        self._engine = _create_engine()
        self._sessions = sessionmaker(self._engine, expire_on_commit=False)
        Base.metadata.create_all(self._engine)
        if self._engine.dialect.name == "postgresql":
            self._enable_row_level_security()

    def _enable_row_level_security(self) -> None:
        with self._engine.begin() as connection:
            connection.execute(text("ALTER TABLE inspections ENABLE ROW LEVEL SECURITY"))
            connection.execute(text("ALTER TABLE inspections FORCE ROW LEVEL SECURITY"))
            connection.execute(
                text(
                    """
                    DO $policy$
                    BEGIN
                        CREATE POLICY inspection_organization_isolation ON inspections
                        USING (org_id = current_setting('app.organization_id', true))
                        WITH CHECK (org_id = current_setting('app.organization_id', true));
                    EXCEPTION
                        WHEN duplicate_object THEN NULL;
                    END
                    $policy$;
                    """
                )
            )

    @staticmethod
    def _set_organization(session: Session, organization_id: str) -> None:
        if not organization_id or not organization_id.strip():
            raise ValueError("organization_id cannot be empty")
        if session.bind is not None and session.bind.dialect.name == "postgresql":
            session.execute(
                text("SELECT set_config('app.organization_id', :organization_id, true)"),
                {"organization_id": organization_id},
            )

    @staticmethod
    def _row(inspection: Inspection, organization_id: str) -> InspectionRow:
        inspection.organization_id = organization_id
        return InspectionRow(
            org_id=organization_id,
            inspection_id=inspection.inspection_id,
            payload=inspection.model_dump(mode="json"),
        )

    def create(self, inspection: Inspection, organization_id: str) -> Inspection:
        try:
            with self._sessions.begin() as session:
                self._set_organization(session, organization_id)
                session.add(self._row(inspection, organization_id))
        except IntegrityError as exc:
            raise ValueError(f"Inspection already exists: {inspection.inspection_id}") from exc
        return inspection

    def list(self, organization_id: str) -> list[Inspection]:
        with self._sessions.begin() as session:
            self._set_organization(session, organization_id)
            rows = session.scalars(
                select(InspectionRow).where(InspectionRow.org_id == organization_id)
            ).all()
            return [Inspection.model_validate(row.payload) for row in rows]

    def get(self, inspection_id: str, organization_id: str) -> Inspection | None:
        with self._sessions.begin() as session:
            self._set_organization(session, organization_id)
            row = session.get(InspectionRow, (organization_id, inspection_id))
            return Inspection.model_validate(row.payload) if row is not None else None

    def update(self, inspection: Inspection, organization_id: str) -> Inspection:
        with self._sessions.begin() as session:
            self._set_organization(session, organization_id)
            row = session.get(InspectionRow, (organization_id, inspection.inspection_id))
            if row is None:
                raise ValueError(f"Inspection not found in organization: {inspection.inspection_id}")
            row.payload = self._row(inspection, organization_id).payload
        return inspection

    def generate_id(self) -> str:
        return f"INS-{uuid4().hex[:8].upper()}"
