"""Repository for `FieldValueEvidence` (CDD-022 §13, §22, §25; Field-Value
Evidence Artifact Authorization). Minimal repository: `create_or_get_existing(...)`,
`get_by_id(...)`, and `get_by_source_field(...)` only -- no update, no
delete, no `get_latest`/`get_current`/`get_best`/`get_valid` selection
method of any kind.

`create_or_get_existing` implements CDD-022 §25's replay guarantee: because
`field_value_evidence_id` is domain-derived and domain-verified from exactly
the four governed semantic identity inputs (`FieldValueEvidence.__post_init__`),
an identity collision under normal operation can only mean identical
replay -- the repository compares the persisted row's own four semantic
fields against the incoming fact's and returns the existing, already-persisted
fact unchanged (never overwriting `received_at`/`evidence_reference`) if they
match, or raises `ValidationException` if they do not (only reachable via
persisted-data corruption, since identity is domain-verified on every
construction). This method contains no identity-derivation logic of its own.

`get_by_source_field` enforces tenant ownership by joining through
`source_fields.source_object_id` -> `source_objects.tenant_id` -- `tenant_id`
is never a stored column on `field_value_evidence` (CDD-022 §7)."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.source_field import SourceFieldORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM


class FieldValueEvidenceRepository(Protocol):
    def create_or_get_existing(self, evidence: FieldValueEvidence) -> FieldValueEvidence: ...

    def get_by_id(self, field_value_evidence_id: UUID) -> FieldValueEvidence | None: ...

    def get_by_source_field(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> tuple[FieldValueEvidence, ...]: ...


class FieldValueEvidenceRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_or_get_existing(self, evidence: FieldValueEvidence) -> FieldValueEvidence:
        existing = self.get_by_id(evidence.field_value_evidence_id.value)
        if existing is None:
            self.session.add(
                FieldValueEvidenceORM(
                    field_value_evidence_id=evidence.field_value_evidence_id.value,
                    source_field_id=evidence.source_field_id.value,
                    source_record_reference=evidence.source_record_reference,
                    observed_representation=evidence.observed_representation,
                    observed_at=evidence.observed_at,
                    received_at=evidence.received_at,
                    evidence_reference=evidence.evidence_reference,
                )
            )
            self.session.flush()
            return evidence

        if (
            existing.source_field_id != evidence.source_field_id
            or existing.source_record_reference != evidence.source_record_reference
            or existing.observed_representation != evidence.observed_representation
            or existing.observed_at != evidence.observed_at
        ):
            raise ValidationException(
                "Field Value Evidence identity conflict: persisted fact's governed semantic "
                f"identity inputs do not match the supplied fact for "
                f"field_value_evidence_id {evidence.field_value_evidence_id.value}"
            )

        return existing

    def get_by_id(self, field_value_evidence_id: UUID) -> FieldValueEvidence | None:
        model = self.session.get(FieldValueEvidenceORM, field_value_evidence_id)
        if model is None:
            return None
        return self._to_domain(model)

    def get_by_source_field(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> tuple[FieldValueEvidence, ...]:
        source_field = self.session.get(SourceFieldORM, source_field_id)
        if source_field is None:
            raise ValidationException(f"SourceField not found: {source_field_id}")

        source_object_tenant_id = self.session.scalar(
            select(SourceObjectORM.tenant_id).where(
                SourceObjectORM.source_object_id == source_field.source_object_id
            )
        )
        if source_object_tenant_id != tenant_id:
            raise ValidationException(
                f"Field Value Evidence tenant ownership mismatch: SourceField {source_field_id} "
                f"does not belong to tenant {tenant_id!r}"
            )

        models = (
            self.session.execute(
                select(FieldValueEvidenceORM)
                .where(FieldValueEvidenceORM.source_field_id == source_field_id)
                .order_by(FieldValueEvidenceORM.field_value_evidence_id)
            )
            .scalars()
            .all()
        )
        return tuple(self._to_domain(model) for model in models)

    @staticmethod
    def _to_domain(model: FieldValueEvidenceORM) -> FieldValueEvidence:
        return FieldValueEvidence(
            field_value_evidence_id=Identifier(model.field_value_evidence_id),
            source_field_id=Identifier(model.source_field_id),
            source_record_reference=model.source_record_reference,
            observed_representation=model.observed_representation,
            observed_at=model.observed_at,
            received_at=model.received_at,
            evidence_reference=model.evidence_reference,
        )
