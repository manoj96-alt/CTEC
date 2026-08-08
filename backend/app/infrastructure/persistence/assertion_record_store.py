import hashlib

from sqlalchemy.orm import Session

from app.domain.assertion_engine import AssertionRecord
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.assertion_record import (
    AssertionRecordEntityResolutionEvidenceModel,
    AssertionRecordHistoryModel,
    AssertionRecordModel,
    AssertionRecordSemanticResolutionEvidenceModel,
)
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.semantic_resolution import SemanticResolutionRecordModel


class AssertionRecordStore:
    """Append immutable records and maintain currentness outside record state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def identity_key(record: AssertionRecord) -> str:
        value = ":".join(
            map(
                str,
                (
                    record.subject_entity_id,
                    record.predicate_relationship_type_id,
                    record.object_institutional_concept_id,
                    record.context_id,
                ),
            )
        )
        return hashlib.sha256(value.encode()).hexdigest()

    def append(self, record: AssertionRecord) -> None:
        self._verify_governed_evidence(record)
        self.session.add(
            AssertionRecordModel(
                record_id=record.record_id,
                subject_entity_id=record.subject_entity_id,
                predicate_relationship_type_id=record.predicate_relationship_type_id,
                object_institutional_concept_id=record.object_institutional_concept_id,
                context_id=record.context_id,
                outcome=record.outcome.value,
                business_confidence=record.business_confidence.value,
                structured_reasons="\n".join(record.structured_reasons),
                narrative_explanation=record.narrative_explanation,
                policy_version=record.policy_version,
                produced_at=record.produced_at,
            )
        )
        for evidence_id in record.evidence.enterprise_entity_resolution_record_ids:
            self.session.add(
                AssertionRecordEntityResolutionEvidenceModel(
                    assertion_record_id=record.record_id, entity_resolution_record_id=evidence_id
                )
            )
        for evidence_id in record.evidence.semantic_resolution_record_ids:
            self.session.add(
                AssertionRecordSemanticResolutionEvidenceModel(
                    assertion_record_id=record.record_id, semantic_resolution_record_id=evidence_id
                )
            )
        key = self.identity_key(record)
        record_history = self.session.get(AssertionRecordHistoryModel, key)
        if record_history is None:
            self.session.add(
                AssertionRecordHistoryModel(
                    assertion_identity_key=key,
                    current_record_identifier=record.record_id,
                    historical_record_references="",
                    updated_at=record.produced_at,
                )
            )
        else:
            historical_references = [
                value for value in record_history.historical_record_references.split(",") if value
            ]
            record_history.historical_record_references = ",".join(
                [*historical_references, str(record_history.current_record_identifier)]
            )
            record_history.current_record_identifier = record.record_id
            record_history.updated_at = record.produced_at

    def _verify_governed_evidence(self, record: AssertionRecord) -> None:
        for evidence_id in record.evidence.enterprise_entity_resolution_record_ids:
            entity_evidence = self.session.get(EnterpriseEntityResolutionRecordModel, evidence_id)
            if (
                entity_evidence is None
                or entity_evidence.enterprise_entity_id != record.subject_entity_id
            ):
                raise ValidationException(
                    "EER evidence must exist and reference the Assertion Subject"
                )
        for evidence_id in record.evidence.semantic_resolution_record_ids:
            semantic_evidence = self.session.get(SemanticResolutionRecordModel, evidence_id)
            if (
                semantic_evidence is None
                or semantic_evidence.enterprise_entity_id != record.subject_entity_id
            ):
                raise ValidationException(
                    "Semantic evidence must exist and reference the Assertion Subject"
                )
