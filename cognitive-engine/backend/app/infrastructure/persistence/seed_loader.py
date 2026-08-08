import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid5
from zipfile import ZipFile

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.bootstrap import (
    BOOTSTRAP_GOVERNANCE_STATUS,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_STATUS,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    SEED_TIMESTAMP,
    SEED_VERSION,
)
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem


@dataclass(frozen=True, slots=True)
class SeedSummary:
    seed_version: str
    csv_files: int
    source_systems_created: int
    source_objects_created: int
    source_systems_total: int
    source_objects_total: int


class SeedLoader:
    """Deterministically persists EDT-001 rows as uninterpreted source provenance."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load(self, archive_path: Path) -> SeedSummary:
        source_systems_created = 0
        source_objects_created = 0
        with ZipFile(archive_path) as archive:
            csv_names = sorted(name for name in archive.namelist() if name.endswith(".csv"))
            dataset_system_id = self._stable_id("source-system", SEED_VERSION)
            if self._session.get(SourceSystem, dataset_system_id) is None:
                self._session.add(self._source_system(dataset_system_id, SEED_VERSION))
                source_systems_created += 1
            self._session.flush()

            for csv_name in csv_names:
                rows = self._read_rows(archive, csv_name)
                if csv_name == "SourceSystems.csv":
                    for row in rows:
                        name = row["SourceSystem"].strip()
                        identifier = self._stable_id("source-system", name)
                        if self._session.get(SourceSystem, identifier) is None:
                            self._session.add(self._source_system(identifier, name))
                            source_systems_created += 1
                for row in rows:
                    canonical_row = json.dumps(row, sort_keys=True, separators=(",", ":"))
                    identifier = self._stable_id(csv_name, canonical_row)
                    if self._session.get(SourceObject, identifier) is not None:
                        continue
                    digest = hashlib.sha256(canonical_row.encode()).hexdigest()[:24]
                    self._session.add(
                        SourceObject(
                            source_object_id=identifier,
                            source_object_name=f"{SEED_VERSION}:{csv_name}:{digest}",
                            lifecycle_state=BOOTSTRAP_STATUS,
                            effective_from=SEED_TIMESTAMP,
                            effective_to=None,
                            governance_status=BOOTSTRAP_GOVERNANCE_STATUS,
                            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                            created_on=SEED_TIMESTAMP,
                            modified_by=None,
                            modified_on=None,
                            version_number=1,
                            previous_version_id=None,
                            source_system_id=dataset_system_id,
                        )
                    )
                    source_objects_created += 1
            self._session.flush()
        return SeedSummary(
            seed_version=SEED_VERSION,
            csv_files=len(csv_names),
            source_systems_created=source_systems_created,
            source_objects_created=source_objects_created,
            source_systems_total=self._count(SourceSystem),
            source_objects_total=self._count(SourceObject),
        )

    def reset(self) -> None:
        prefix = f"{SEED_VERSION}:%"
        self._session.execute(
            delete(SourceObject).where(SourceObject.source_object_name.like(prefix))
        )
        seeded_system_ids = select(SourceSystem.source_system_id).where(
            SourceSystem.created_by == BOOTSTRAP_SYSTEM_ENTITY_ID,
            SourceSystem.created_on == SEED_TIMESTAMP,
        )
        self._session.execute(
            delete(SourceSystem).where(SourceSystem.source_system_id.in_(seeded_system_ids))
        )

    def verify_counts(self, archive_path: Path) -> dict[str, int]:
        with ZipFile(archive_path) as archive:
            expected_objects = sum(
                len(self._read_rows(archive, name))
                for name in archive.namelist()
                if name.endswith(".csv")
            )
        actual_objects = self._session.scalar(
            select(func.count())
            .select_from(SourceObject)
            .where(SourceObject.source_object_name.like(f"{SEED_VERSION}:%"))
        )
        return {
            "expected_source_objects": expected_objects,
            "actual_source_objects": actual_objects or 0,
        }

    @staticmethod
    def _read_rows(archive: ZipFile, name: str) -> list[dict[str, str]]:
        content = archive.read(name).decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(content)))

    @staticmethod
    def _stable_id(category: str, value: str) -> UUID:
        return uuid5(BOOTSTRAP_SEED_NAMESPACE, f"{category}:{value}")

    @staticmethod
    def _source_system(identifier: UUID, name: str) -> SourceSystem:
        return SourceSystem(
            source_system_id=identifier,
            source_system_name=name,
            lifecycle_state=BOOTSTRAP_STATUS,
            effective_from=SEED_TIMESTAMP,
            effective_to=None,
            governance_status=BOOTSTRAP_GOVERNANCE_STATUS,
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=SEED_TIMESTAMP,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
        )

    def _count(self, model_type: type[SourceSystem] | type[SourceObject]) -> int:
        return self._session.scalar(select(func.count()).select_from(model_type)) or 0
