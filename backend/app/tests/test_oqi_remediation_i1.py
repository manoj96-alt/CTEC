"""Real-PostgreSQL acceptance evidence for OQI5-I1 -- Deterministic
Remediation Foundation (CDD-043 §11-§17, §25; Artifact Authorization §2
row 9). Proves: migration schema correctness and the 86->90->86->90
round trip; OQI2 candidate extraction from real
`quality_comparison_evaluation_*` rows preserves dissent (multiple
distinct candidate values, never collapsed to a majority) and
missingness (every candidate for a target records every genuinely
missing participant role); OQI1/OQI3 Findings deterministically yield
zero candidates and route to `STEWARD_INVESTIGATION`; a reopened Finding
reuses its existing `RemediationCase` identity; the full
`RemediationAuthorization` lifecycle -- request, self-approval denial,
cross-tenant denial, approve, one-time consumption, a genuinely
concurrent decide race serialized by the same row-lock technique Gate S
uses, and the Finding-revision staleness contract failing closed with
`REMEDIATION_ACTION_MISMATCH` -- all against real Postgres; and the
central re-evaluation invariant: an external-execution report alone never
resolves a case, only a subsequent read of the Finding's own,
independently re-evaluated `RESOLVED` status does."""

# isort: skip_file
from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_cross_source_evaluation_service import OqiCrossSourceEvaluationService
from app.application.oqi_remediation_service import OqiRemediationError, OqiRemediationService
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.quality_rule import QualityRule
from app.domain.oqi_cross_source.correspondence import ComparisonSubjectCorrespondence
from app.domain.oqi_cross_source.evaluation import derive_comparison_finding_id
from app.domain.oqi_remediation.case import FindingFamily, RemediationCaseStatus
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.oqi_business_rule import BusinessRuleORM
from app.infrastructure.persistence.models.oqi_business_rule_evaluation import (
    BusinessRuleEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_cross_source_evaluation import (
    QualityComparisonEvaluationEvidenceORM,
    QualityComparisonEvaluationObservationORM,
    QualityComparisonEvaluationORM,
    QualityComparisonEvaluationParticipantORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
    OqiCrossSourceCorrespondenceRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
    OqiCrossSourceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.tests.test_oqi_cross_source_postgres import _correspondence, _rule, _seed_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = NOW + timedelta(days=1)


def _service(session: Session) -> OqiRemediationService:
    return OqiRemediationService(
        repository=OqiRemediationRepositoryImpl(session),
        participant_reader=OqiRemediationParticipantReader(session),
    )


def _admit_field_value_evidence(
    session: Session,
    *,
    source_field_id: UUID,
    value: str,
    reference: str,
    observed_at: datetime = NOW,
    received_at: datetime = NOW,
) -> UUID:
    evidence_id = uuid4()
    session.add(
        FieldValueEvidenceORM(
            field_value_evidence_id=evidence_id,
            source_field_id=source_field_id,
            source_record_reference=reference,
            observed_representation=value,
            observed_at=observed_at,
            received_at=received_at,
        )
    )
    session.flush()
    return evidence_id


def _seed_oqi1_finding(session: Session, *, tenant_id: str, status: str = "OPEN") -> UUID:
    object_id, field_id = _seed_field(session, tenant_id=tenant_id, field_label="LFA1-COUNTRY")
    finding_id = uuid4()
    session.add(
        QualityFindingORM(
            finding_id=finding_id,
            tenant_id=tenant_id,
            quality_condition_id=f"cond-{uuid4()}",
            subject_type="SINGLE_RECORD",
            source_object_id=object_id,
            source_record_reference="REC-1",
            source_field_id=field_id,
            finding_type="MISSING_VALUE",
            status=status,
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    session.flush()
    return finding_id


def _seed_oqi3_finding(session: Session, *, tenant_id: str, status: str = "OPEN") -> UUID:
    object_id, field_id = _seed_field(session, tenant_id=tenant_id, field_label="MARC-PGRP")
    rule_id = uuid4()
    session.add(
        BusinessRuleORM(
            rule_id=rule_id,
            business_condition_id=f"cond-{uuid4()}",
            version=1,
            tenant_id=tenant_id,
            rule_family="CONDITIONAL_REQUIRED",
            applicability=None,
            predicate={
                "clause_id": "x",
                "operator": "IS_NOT_NULL",
                "input_role": "purchasing_group",
            },
            status="ACTIVE",
            created_by="tester",
            created_on=NOW,
        )
    )
    evaluation_id = uuid4()
    session.add(
        BusinessRuleEvaluationORM(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            business_condition_id=f"cond-{uuid4()}",
            rule_id=rule_id,
            subject_type="SINGLE_RECORD",
            source_object_id=object_id,
            source_record_reference="REC-1",
            evaluation_mode="CURRENT_STATE",
            evaluation_horizon=NOW,
            input_evidence_digest="0" * 64,
            outcome="VIOLATED",
            evaluated_at=NOW,
        )
    )
    finding_id = uuid4()
    session.add(
        BusinessRuleFindingORM(
            finding_id=finding_id,
            tenant_id=tenant_id,
            business_condition_id=f"cond-{uuid4()}",
            subject_type="SINGLE_RECORD",
            subject_identity=f"{object_id}:REC-1",
            status=status,
            resolution_basis=None if status == "OPEN" else "SATISFIED",
            latest_evaluation_id=evaluation_id,
            occurrence_count=1,
            reopen_count=0,
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
    )
    session.flush()
    _ = field_id
    return finding_id


def _seed_oqi2_finding(
    session: Session,
    *,
    tenant_id: str,
    roles: dict[str, str | None],
    conflicting_roles: set[str],
    missing_roles: set[str],
    authoritative_role: str | None,
) -> tuple[UUID, UUID]:
    """Hand-builds one real OQI2 evaluation + its participant/evidence/
    observation rows directly against `quality_comparison_evaluation_*`
    (the same technique this repository's own postgres test suite uses
    for its FK/constraint-focused tests) -- and the `QualityComparisonFinding`
    read-model row that references it. `roles` maps role -> observed value
    (`None` for a role with zero admitted evidence)."""
    condition_id = f"cond-{uuid4()}"
    role_names = list(roles.keys())
    object_a, field_a = _seed_field(session, tenant_id=tenant_id, field_label=f"F-{role_names[0]}")
    object_b, field_b = _seed_field(
        session,
        tenant_id=tenant_id,
        field_label=f"F-{role_names[1] if len(role_names) > 1 else role_names[0]}",
    )
    rule = _rule(condition_id=condition_id, sap_field=field_a, plm_field=field_b)
    OqiQualityRuleRepositoryImpl(session).create(rule)
    subject_id = uuid4()
    OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
        _correspondence(
            tenant_id=tenant_id, subject_id=subject_id, sap_object=object_a, plm_object=object_b
        )
    )

    correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
        tenant_id=tenant_id, comparison_subject_id=subject_id
    )
    assert correspondence is not None
    evaluation_id = uuid4()
    session.add(
        QualityComparisonEvaluationORM(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            quality_condition_id=condition_id,
            rule_id=rule.rule_id,
            rule_version=1,
            subject_type="CROSS_SOURCE_COMPARISON",
            comparison_subject_id=subject_id,
            comparison_subject_correspondence_id=correspondence.correspondence_id,
            evaluation_mode="CURRENT_STATE",
            evaluation_origin="RULE_DETERMINISTIC",
            evaluation_horizon=NOW,
            participant_evidence_digest="0" * 64,
            outcome="VIOLATED",
            applied_current_state_authority=True,
            state_revision_applied=1,
            evaluated_on=NOW,
        )
    )
    session.flush()

    # Roles the correspondence itself names (only ever "SAP"/"PLM", fixed
    # by `_correspondence()`) get their evidence admitted under that same
    # correspondence-declared `source_record_reference` -- the exact
    # lineage key the real OQI2 evaluator's evidence-selection queries
    # key off of. Extra roles beyond the correspondence's two members
    # (e.g. the N=5 dissent test's R1-R5) fall back to a synthetic
    # per-role reference, since no real evaluator call is ever exercised
    # against those roles.
    reference_by_role = {
        member.participant_role: member.source_record_reference for member in correspondence.members
    }

    evidence_by_role: dict[str, UUID] = {}
    for role, value in roles.items():
        object_id, field_id = (object_a, field_a) if role == role_names[0] else (object_b, field_b)
        reference = reference_by_role.get(role, f"REC-{role}")
        session.add(
            QualityComparisonEvaluationParticipantORM(
                evaluation_id=evaluation_id,
                participant_role=role,
                source_field_id=field_id,
                source_object_id=object_id,
                source_record_reference=reference,
                expected=True,
                authoritative=(role == authoritative_role),
            )
        )
        if value is not None:
            evidence_id = _admit_field_value_evidence(
                session, source_field_id=field_id, value=value, reference=reference
            )
            evidence_by_role[role] = evidence_id
            session.add(
                QualityComparisonEvaluationEvidenceORM(
                    evaluation_id=evaluation_id,
                    participant_role=role,
                    source_field_id=field_id,
                    field_value_evidence_id=evidence_id,
                    sequence_index=0,
                )
            )
    session.flush()
    for role in conflicting_roles:
        session.add(
            QualityComparisonEvaluationObservationORM(
                evaluation_id=evaluation_id,
                observation_type="CROSS_SOURCE_VALUE_CONFLICT",
                participant_role=role,
            )
        )
    for role in missing_roles:
        session.add(
            QualityComparisonEvaluationObservationORM(
                evaluation_id=evaluation_id,
                observation_type="CROSS_SOURCE_PARTICIPANT_VALUE_MISSING",
                participant_role=role,
            )
        )

    # Real, deterministic Finding identity (CDD-040 §32) -- not a random
    # UUID. This is what lets a later real `evaluate_current_state` call
    # find and resolve *this exact* Finding rather than fabricate a new
    # one under an identity it cannot recognize.
    finding_id = derive_comparison_finding_id(
        tenant_id=tenant_id,
        quality_condition_id=condition_id,
        comparison_subject_id=subject_id,
    )
    session.add(
        QualityComparisonFindingORM(
            finding_id=finding_id,
            tenant_id=tenant_id,
            quality_condition_id=condition_id,
            subject_type="CROSS_SOURCE_COMPARISON",
            comparison_subject_id=subject_id,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
            latest_evaluation_id=evaluation_id,
        )
    )
    session.flush()
    return finding_id, evaluation_id


# --- migration ---


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    tables = set(inspect(migrated_engine).get_table_names())
    for expected in (
        "oqi_remediation_cases",
        "oqi_remediation_candidates",
        "oqi_remediation_instructions",
        "oqi_remediation_authorizations",
    ):
        assert expected in tables


def test_migration_round_trips_86_90_86_90(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    def _table_count() -> int:
        with migrated_engine.connect() as connection:
            return int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_type='BASE TABLE' "
                        "AND table_name != 'alembic_version'"
                    )
                ).scalar_one()
            )

    # CDD-048 (OQI-H2-I-R1 narrow correction, disclosed in the OQI-H2-I
    # final report; OQI-H3-I-R1 amendment): mechanically re-pinned from 109 to 114.
    assert _table_count() == 120
    alembic.command.downgrade(config, "0023_oqi4_ontology_impact")
    assert _table_count() == 86
    alembic.command.upgrade(config, "0024_oqi5_remediation")
    assert _table_count() == 90
    # Restore the session-scoped `migrated_engine` fixture to full head
    # before returning control -- this test intentionally lands mid-chain
    # at I1's own revision to prove its own isolated round trip, but the
    # fixture is shared (scope="session") across the entire suite; leaving
    # the database parked at 0024 would silently break every later test
    # in the same session that expects the true current head (94 tables),
    # a latent defect only OQI5-I2's own migration 0025 exposes (until now
    # 0024 always coincided with head, since I1 was the last migration).
    alembic.command.upgrade(config, "head")
    assert _table_count() == 120


# --- OQI1 / OQI3: zero candidates by design ---


def test_oqi1_finding_yields_zero_candidates_and_steward_investigation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id = _seed_oqi1_finding(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        case, candidates = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        session.commit()

    assert candidates == ()
    assert case.status is RemediationCaseStatus.STEWARD_INVESTIGATION


def test_oqi3_finding_yields_zero_candidates_and_steward_investigation(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id = _seed_oqi3_finding(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        case, candidates = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI3, finding_id=finding_id
        )
        session.commit()

    assert candidates == ()
    assert case.status is RemediationCaseStatus.STEWARD_INVESTIGATION


def test_finding_not_found_fails_closed(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _service(session).extract_candidates(
                tenant_id=f"tenant-{uuid4()}",
                finding_family=FindingFamily.OQI1,
                finding_id=uuid4(),
            )
        assert excinfo.value.code == "REMEDIATION_FINDING_NOT_FOUND"


# --- OQI2: dissent + missingness preservation, N=5 ---


def test_oqi2_extraction_preserves_dissent_and_missingness_n5(migrated_engine: Engine) -> None:
    """5 participants: R1/R2 agree on "ALPHA", R3/R4 agree on "BETA" (a
    genuine 2-vs-2 dissent with no majority), R2 is authoritative, R5 has
    no evidence at all (genuinely missing). No candidate collapses R1-R4's
    disagreement into one "winning" value, and every candidate proposed
    for a disagreeing target still records R5 as missing context."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={"R1": "ALPHA", "R2": "ALPHA", "R3": "BETA", "R4": "BETA", "R5": None},
            conflicting_roles={"R1", "R2", "R3", "R4"},
            missing_roles={"R5"},
            authoritative_role="R2",
        )
        session.commit()

    with factory() as session:
        case, candidates = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()

    assert case.status is RemediationCaseStatus.CANDIDATE_READY
    assert len(candidates) > 0

    # Every remediable target (R1-R5 are all either conflicting or
    # missing) gets its own candidate group; across all of them, both
    # "ALPHA" (R2, authoritative) and "BETA" (R3+R4) appear as
    # independent, equally-real candidates -- dissent is never collapsed,
    # and the 2-supporter "BETA" cluster does not win merely by count
    # (majority != truth).
    values = {c.proposed_value for c in candidates}
    assert {"ALPHA", "BETA"}.issubset(values)

    # Every candidate group built while R5 is one of the "other"
    # participants must record R5 as missing (missingness is never
    # silently dropped); R5's own candidate group (built from R1-R4 only)
    # naturally has no missing participants among *its* pool.
    assert any(candidate.missing_participant_roles == ("R5",) for candidate in candidates)

    # The candidate carrying "ALPHA" (R2's value) is annotated as matching
    # the authoritative participant -- metadata only, not a truth claim:
    # the "BETA" candidate (2 supporters) remains an equally valid entry.
    alpha_candidates = [c for c in candidates if c.proposed_value == "ALPHA"]
    assert any(c.authority_participant_role == "R2" for c in alpha_candidates)
    beta_candidates = [c for c in candidates if c.proposed_value == "BETA"]
    assert all(c.authority_participant_role is None for c in beta_candidates)


def test_oqi2_extraction_is_idempotent_on_replay(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={"SAP": "OLD", "PLM": "NEW"},
            conflicting_roles={"SAP", "PLM"},
            missing_roles=set(),
            authoritative_role="PLM",
        )
        session.commit()

    with factory() as session:
        case_1, candidates_1 = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    with factory() as session:
        case_2, candidates_2 = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()

    assert case_1.case_id == case_2.case_id
    assert {c.candidate_id for c in candidates_1} == {c.candidate_id for c in candidates_2}


def test_case_reopen_reuses_case_identity(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={"SAP": "OLD", "PLM": "NEW"},
            conflicting_roles={"SAP", "PLM"},
            missing_roles=set(),
            authoritative_role="PLM",
        )
        session.commit()

    with factory() as session:
        first_case, _ = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()

    # Simulate a reopen: bump the Finding's own state_revision (the real
    # evaluator's job; here it is asserted as a precondition fact).
    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None
        finding.state_revision = 2
        session.commit()

    with factory() as session:
        second_case, _ = _service(session).extract_candidates(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()

    assert first_case.case_id == second_case.case_id


# --- RemediationAuthorization lifecycle ---


def _seed_authorization(
    session: Session, *, tenant_id: str, requested_by: str = "requester"
) -> tuple[UUID, UUID, UUID]:
    """Returns (finding_id, instruction_id, authorization_id) for a fresh
    OQI2 2-participant conflict, fully wired through extraction ->
    instruction construction -> authorization request."""
    finding_id, _ = _seed_oqi2_finding(
        session,
        tenant_id=tenant_id,
        roles={"SAP": "OLD", "PLM": "NEW"},
        conflicting_roles={"SAP", "PLM"},
        missing_roles=set(),
        authoritative_role="PLM",
    )
    session.commit()
    service = _service(session)
    _, candidates = service.extract_candidates(
        tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
    )
    session.commit()
    instruction = service.construct_instruction(
        tenant_id=tenant_id, candidate_id=candidates[0].candidate_id, created_by="system"
    )
    session.commit()
    authorization = service.request_authorization(
        tenant_id=tenant_id, instruction_id=instruction.instruction_id, requested_by=requested_by
    )
    session.commit()
    return finding_id, instruction.instruction_id, authorization.authorization_id


def test_authorization_self_approval_denied(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        _, _, authorization_id = _seed_authorization(session, tenant_id=tenant_id)

    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _service(session).approve(
                tenant_id=tenant_id, authorization_id=authorization_id, decided_by="requester"
            )
        assert excinfo.value.code == "REMEDIATION_SELF_APPROVAL_PROHIBITED"


def test_authorization_cross_tenant_denied(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        _, _, authorization_id = _seed_authorization(session, tenant_id=tenant_id)

    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _service(session).approve(
                tenant_id=f"tenant-{uuid4()}",
                authorization_id=authorization_id,
                decided_by="approver",
            )
        assert excinfo.value.code == "REMEDIATION_TENANT_MISMATCH"


def test_authorization_approve_then_report_execution_then_one_time_consumption(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        _, _, authorization_id = _seed_authorization(session, tenant_id=tenant_id)

    with factory() as session:
        approved = _service(session).approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="approver"
        )
        session.commit()
    assert approved.status.value == "APPROVED"

    with factory() as session:
        case = _service(session).report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()
    assert case.status is RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED
    assert case.external_execution_claimed is True

    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _service(session).report_external_execution(
                tenant_id=tenant_id, authorization_id=authorization_id
            )
        assert excinfo.value.code == "REMEDIATION_AUTHORIZATION_ALREADY_CONSUMED"


def test_finding_revision_change_before_execution_fails_closed(migrated_engine: Engine) -> None:
    """CDD-043 §15 staleness contract: the payload digest binds
    `finding_state_revision`; if the Finding's own revision advances
    (an independent re-evaluation ran) after authorization but before
    execution, the recomputed digest no longer matches and execution
    fails closed with `REMEDIATION_ACTION_MISMATCH` -- zero extra
    machinery."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _, authorization_id = _seed_authorization(session, tenant_id=tenant_id)

    with factory() as session:
        _service(session).approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="approver"
        )
        session.commit()

    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None
        finding.state_revision = 99
        session.commit()

    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _service(session).report_external_execution(
                tenant_id=tenant_id, authorization_id=authorization_id
            )
        assert excinfo.value.code == "REMEDIATION_ACTION_MISMATCH"


def test_concurrent_approve_race_serializes_to_one_winner(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as setup_session:
        _, _, authorization_id = _seed_authorization(setup_session, tenant_id=tenant_id)

    barrier = threading.Barrier(2)
    outcomes: dict[str, str] = {}

    def _worker(session: Session, key: str, decided_by: str) -> None:
        try:
            barrier.wait(timeout=5)
            _service(session).approve(
                tenant_id=tenant_id, authorization_id=authorization_id, decided_by=decided_by
            )
            session.commit()
            outcomes[key] = "approved"
        except OqiRemediationError as exc:
            session.rollback()
            outcomes[key] = exc.code
        except BaseException as exc:  # noqa: BLE001
            session.rollback()
            outcomes[key] = f"error:{exc!r}"

    session_a, session_b = factory(), factory()
    thread_a = threading.Thread(target=_worker, args=(session_a, "a", "approver-a"))
    thread_b = threading.Thread(target=_worker, args=(session_b, "b", "approver-b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=15)
    thread_b.join(timeout=15)
    session_a.close()
    session_b.close()

    values = list(outcomes.values())
    assert values.count("approved") == 1
    assert values.count("REMEDIATION_AUTHORIZATION_NOT_PENDING") == 1


# --- tenant isolation ---


def test_finding_state_read_is_tenant_isolated(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id = _seed_oqi1_finding(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        with pytest.raises(OqiRemediationError) as excinfo:
            _service(session).extract_candidates(
                tenant_id=f"tenant-{uuid4()}",
                finding_family=FindingFamily.OQI1,
                finding_id=finding_id,
            )
        assert excinfo.value.code == "REMEDIATION_FINDING_NOT_FOUND"


# --- re-evaluation invariant ---


def _load_rule_and_correspondence(
    session: Session, *, tenant_id: str, finding_id: UUID
) -> tuple[QualityRule, ComparisonSubjectCorrespondence]:
    finding = session.get(QualityComparisonFindingORM, finding_id)
    assert finding is not None
    rule = OqiQualityRuleRepositoryImpl(session).get_active(finding.quality_condition_id)
    assert rule is not None
    correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(session).get_active(
        tenant_id=tenant_id, comparison_subject_id=finding.comparison_subject_id
    )
    assert correspondence is not None
    return rule, correspondence


def _participant_target(
    *, rule: QualityRule, correspondence: ComparisonSubjectCorrespondence, role: str
) -> tuple[UUID, str]:
    """The exact `(source_field_id, source_record_reference)` pair the real
    OQI2 evaluator itself uses to select a participant's evidence (field id
    from the rule's participant configuration, record reference from the
    ACTIVE correspondence) -- never a test-only shortcut identifier."""
    field_id = next(
        UUID(entry["source_field_id"])
        for entry in rule.rule_parameters["participants"]
        if entry["role"] == role
    )
    reference = next(
        member.source_record_reference
        for member in correspondence.members
        if member.participant_role == role
    )
    return field_id, reference


def test_fresh_evidence_and_real_oqi2_evaluator_resolve_finding_execution_report_does_not(
    migrated_engine: Engine,
) -> None:
    """Positive crown proof (CDD-043 governing principle): an external/
    manual remediation report carries no truth weight by itself. Only
    fresh, genuinely new immutable `FieldValueEvidence` followed by a real,
    unmodified invocation of OQI2's own `OqiCrossSourceEvaluationService.
    evaluate_current_state` -- never a direct Finding mutation -- resolves
    the Finding, and OQI5's case read-linkage observes that same result."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, instruction_id, authorization_id = _seed_authorization(
            session, tenant_id=tenant_id
        )

    with factory() as session:
        _service(session).approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="approver"
        )
        session.commit()

    with factory() as session:
        case = _service(session).report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()
    assert case.status is RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED

    with factory() as session:
        authorization_before = OqiRemediationRepositoryImpl(session).get_authorization_by_id(
            authorization_id
        )
        assert authorization_before is not None

    # The execution report alone changes nothing about the Finding: a
    # fresh read (new session, not the already-loaded object) proves it
    # is still OPEN. This is the "execution success != quality success"
    # midpoint.
    with factory() as session:
        finding_before = session.get(QualityComparisonFindingORM, finding_id)
        assert finding_before is not None
        assert finding_before.status == "OPEN"
        original_state_revision = finding_before.state_revision

    with factory() as session:
        refreshed = _service(session).refresh_case(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    assert refreshed.status is RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED

    # Fresh, genuinely new immutable evidence arrives -- SAP now agrees
    # with PLM's authoritative value ("NEW"). The original "OLD" evidence
    # row is never mutated. `observed_at`/`received_at` are unambiguously
    # later than the original evidence's `NOW`, avoiding the known
    # OQI-P3-006 equal-timestamp tie ambiguity.
    with factory() as session:
        rule, correspondence = _load_rule_and_correspondence(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        sap_field_id, sap_reference = _participant_target(
            rule=rule, correspondence=correspondence, role="SAP"
        )
        _admit_field_value_evidence(
            session,
            source_field_id=sap_field_id,
            value="NEW",
            reference=sap_reference,
            observed_at=LATER,
            received_at=LATER,
        )
        session.commit()

    # The real, existing, unmodified OQI2 evaluator -- not a fake
    # lifecycle helper, not a direct Finding mutation -- is what decides.
    with factory() as session:
        rule, correspondence = _load_rule_and_correspondence(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        evaluator = OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session),
            clock=lambda: LATER + timedelta(hours=1),
        )
        evaluation = evaluator.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED

    # Fresh read (a brand-new session/object, never the one the evaluator
    # just used): the SAME stable Finding identity is now RESOLVED.
    with factory() as session:
        finding_after = session.get(QualityComparisonFindingORM, finding_id)
        assert finding_after is not None
        assert finding_after.finding_id == finding_id
        assert finding_after.status == "RESOLVED"
        assert finding_after.state_revision == original_state_revision + 1
        # A genuine, persisted evaluation ledger row exists -- resolution
        # is never inferred from Finding status alone.
        persisted_evaluation = session.get(QualityComparisonEvaluationORM, evaluation.evaluation_id)
        assert persisted_evaluation is not None
        assert persisted_evaluation.outcome == "SATISFIED"
        assert finding_after.latest_evaluation_id == evaluation.evaluation_id

    with factory() as session:
        refreshed_again = _service(session).refresh_case(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    assert refreshed_again.status is RemediationCaseStatus.RESOLVED
    # Same, stable RemediationCase identity -- not a new case.
    assert refreshed_again.case_id == case.case_id

    # The prior remediation history (candidate -> instruction ->
    # authorization -> execution report) is immutable through this
    # re-evaluation: the authorization's own digest/consumption facts are
    # unchanged, and the instruction it points to is unchanged.
    with factory() as session:
        authorization_after = OqiRemediationRepositoryImpl(session).get_authorization_by_id(
            authorization_id
        )
        assert authorization_after is not None
        assert authorization_after.payload_digest == authorization_before.payload_digest
        assert authorization_after.consumed_on == authorization_before.consumed_on
        assert authorization_after.instruction_id == instruction_id
        instruction = OqiRemediationRepositoryImpl(session).get_instruction(instruction_id)
        assert instruction is not None
        assert instruction.instruction_id == instruction_id


def test_fresh_evidence_still_violated_leaves_finding_open_execution_report_does_not_resolve(
    migrated_engine: Engine,
) -> None:
    """Negative crown proof: fresh evidence that arrives after a reported
    external remediation but that still leaves the cross-source values in
    conflict must leave the same Finding OPEN -- the real OQI2 evaluator,
    not the execution report, is what decided that, too."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _, authorization_id = _seed_authorization(session, tenant_id=tenant_id)

    with factory() as session:
        _service(session).approve(
            tenant_id=tenant_id, authorization_id=authorization_id, decided_by="approver"
        )
        session.commit()

    with factory() as session:
        case = _service(session).report_external_execution(
            tenant_id=tenant_id, authorization_id=authorization_id
        )
        session.commit()
    assert case.status is RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED

    with factory() as session:
        finding_before = session.get(QualityComparisonFindingORM, finding_id)
        assert finding_before is not None
        assert finding_before.status == "OPEN"
        original_state_revision = finding_before.state_revision

    # Fresh, genuinely new immutable evidence arrives, but SAP's new value
    # ("OLDER") still disagrees with PLM's authoritative "NEW" -- the
    # quality condition remains genuinely violated.
    with factory() as session:
        rule, correspondence = _load_rule_and_correspondence(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        sap_field_id, sap_reference = _participant_target(
            rule=rule, correspondence=correspondence, role="SAP"
        )
        _admit_field_value_evidence(
            session,
            source_field_id=sap_field_id,
            value="OLDER",
            reference=sap_reference,
            observed_at=LATER,
            received_at=LATER,
        )
        session.commit()

    with factory() as session:
        rule, correspondence = _load_rule_and_correspondence(
            session, tenant_id=tenant_id, finding_id=finding_id
        )
        evaluator = OqiCrossSourceEvaluationService(
            evaluation_repository=OqiCrossSourceEvaluationRepositoryImpl(session),
            clock=lambda: LATER + timedelta(hours=1),
        )
        evaluation = evaluator.evaluate_current_state(rule=rule, correspondence=correspondence)
        session.commit()
    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED

    # Fresh read: the SAME Finding identity remains OPEN.
    with factory() as session:
        finding_after = session.get(QualityComparisonFindingORM, finding_id)
        assert finding_after is not None
        assert finding_after.finding_id == finding_id
        assert finding_after.status == "OPEN"
        assert finding_after.state_revision == original_state_revision + 1
        persisted_evaluation = session.get(QualityComparisonEvaluationORM, evaluation.evaluation_id)
        assert persisted_evaluation is not None
        assert persisted_evaluation.outcome == "VIOLATED"

    with factory() as session:
        refreshed_again = _service(session).refresh_case(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    assert refreshed_again.status is RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED
    assert refreshed_again.case_id == case.case_id
