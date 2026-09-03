"""Repository for OQI-H3 governed Canonical Standard persistence and
deterministic resolution (CDD-049 §8-§13; Artifact Authorization row 3).

`acquire_canonical_standard_authority` follows the exact mechanism every
other OQI advisory lock uses. Seed `7` is the next available value in the
OQI advisory-lock seed registry (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6,
5=OQI-H1 coverage, 6=Reference Evidence) -- distinct from every existing
seed.

`get_active_standard_for_information_element` is the single query the
Conformity evaluator and the Consistency canonical-projection gate (CDD-049
§16) both consume -- resolution is anchored exclusively to
`information_element_requirement_id` (PO-H3-01), never to a `SourceField`.
Eagerly loads the full value/alias tree so `canonicalize()` (a pure,
in-memory function) can be applied without further queries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_canonical_standard.standard import (
    CanonicalAlias,
    CanonicalStandard,
    CanonicalStandardStatus,
    CanonicalValue,
)
from app.infrastructure.persistence.models.oqi_canonical_standard import (
    CanonicalStandardAliasORM,
    CanonicalStandardORM,
    CanonicalStandardValueORM,
)

#: CDD-049 §9 unauthorized-paths note: next available value in the OQI
#: advisory-lock seed registry (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6,
#: 5=OQI-H1 coverage, 6=Reference Evidence).
OQI_CANONICAL_STANDARD_ADVISORY_LOCK_SEED = 7


class OqiCanonicalStandardRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Advisory lock (dedicated seed 7).
    # ------------------------------------------------------------------

    def acquire_canonical_standard_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_CANONICAL_STANDARD_ADVISORY_LOCK_SEED},
        )

    # ------------------------------------------------------------------
    # Standard persistence.
    # ------------------------------------------------------------------

    def insert_standard(self, standard: CanonicalStandard) -> None:
        """A plain insert -- standard versions are immutable, never
        upserted. The database's partial unique index enforces "at most one
        ACTIVE version per Information Element"; this method does not
        pre-check, so a violation surfaces as a real `IntegrityError`."""
        self.session.add(
            CanonicalStandardORM(
                canonical_standard_id=standard.canonical_standard_id,
                information_element_requirement_id=standard.information_element_requirement_id,
                version_number=standard.version_number,
                previous_version_id=standard.previous_version_id,
                status=standard.status.value,
                created_by=standard.created_by,
                created_on=standard.created_on,
                retired_on=standard.retired_on,
            )
        )
        self.session.flush()
        for value in standard.values:
            self.session.add(
                CanonicalStandardValueORM(
                    canonical_value_id=value.canonical_value_id,
                    canonical_standard_id=value.canonical_standard_id,
                    canonical_representation=value.canonical_representation,
                )
            )
        # Explicit flush before the alias child rows -- the FK dependency
        # (alias -> value) must be physically committed first, mirroring
        # ReferenceEvidenceAssertionORM's own two-phase flush discipline
        # (CDD-048 §15) rather than relying on implicit ORM insert-ordering.
        self.session.flush()
        for value in standard.values:
            for alias in value.aliases:
                self.session.add(
                    CanonicalStandardAliasORM(
                        canonical_alias_id=alias.canonical_alias_id,
                        canonical_value_id=alias.canonical_value_id,
                        canonical_standard_id=value.canonical_standard_id,
                        alias_representation=alias.alias_representation,
                    )
                )
        self.session.flush()

    def retire_standard(self, *, canonical_standard_id: UUID, retired_on: datetime) -> None:
        model = self.session.get(CanonicalStandardORM, canonical_standard_id)
        if model is None:
            raise ValueError(f"no CanonicalStandard {canonical_standard_id}")
        model.status = CanonicalStandardStatus.RETIRED.value
        model.retired_on = retired_on

    def get_active_standard_for_information_element(
        self, *, information_element_requirement_id: UUID
    ) -> CanonicalStandard | None:
        model = (
            self.session.query(CanonicalStandardORM)
            .filter(
                CanonicalStandardORM.information_element_requirement_id
                == information_element_requirement_id,
                CanonicalStandardORM.status == CanonicalStandardStatus.ACTIVE.value,
            )
            .one_or_none()
        )
        return None if model is None else self._standard_to_domain(model)

    def get_latest_standard_version_for_information_element(
        self, *, information_element_requirement_id: UUID
    ) -> CanonicalStandard | None:
        model = (
            self.session.query(CanonicalStandardORM)
            .filter(
                CanonicalStandardORM.information_element_requirement_id
                == information_element_requirement_id,
            )
            .order_by(CanonicalStandardORM.version_number.desc())
            .first()
        )
        return None if model is None else self._standard_to_domain(model)

    def _standard_to_domain(self, model: CanonicalStandardORM) -> CanonicalStandard:
        value_models = (
            self.session.execute(
                select(CanonicalStandardValueORM).where(
                    CanonicalStandardValueORM.canonical_standard_id == model.canonical_standard_id
                )
            )
            .scalars()
            .all()
        )
        alias_models = (
            self.session.execute(
                select(CanonicalStandardAliasORM).where(
                    CanonicalStandardAliasORM.canonical_standard_id == model.canonical_standard_id
                )
            )
            .scalars()
            .all()
        )
        aliases_by_value_id: dict[UUID, list[CanonicalAlias]] = {}
        for alias_model in alias_models:
            aliases_by_value_id.setdefault(alias_model.canonical_value_id, []).append(
                CanonicalAlias(
                    canonical_alias_id=alias_model.canonical_alias_id,
                    canonical_value_id=alias_model.canonical_value_id,
                    alias_representation=alias_model.alias_representation,
                )
            )
        values = tuple(
            CanonicalValue(
                canonical_value_id=value_model.canonical_value_id,
                canonical_standard_id=value_model.canonical_standard_id,
                canonical_representation=value_model.canonical_representation,
                aliases=tuple(aliases_by_value_id.get(value_model.canonical_value_id, ())),
            )
            for value_model in value_models
        )
        return CanonicalStandard(
            canonical_standard_id=model.canonical_standard_id,
            information_element_requirement_id=model.information_element_requirement_id,
            version_number=model.version_number,
            previous_version_id=model.previous_version_id,
            status=CanonicalStandardStatus(model.status),
            created_by=model.created_by,
            created_on=model.created_on,
            values=values,
            retired_on=model.retired_on,
        )
