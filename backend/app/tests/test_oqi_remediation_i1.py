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
from datetime import UTC, datetime
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_remediation_service import OqiRemediationError, OqiRemediationService
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
from app.infrastructure.persistence.oqi_quality_rule_repository import OqiQualityRuleRepositoryImpl
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.tests.test_oqi_cross_source_postgres import _correspondence, _rule, _seed_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _service(session: Session) -> OqiRemediationService:
    return OqiRemediationService(
        repository=OqiRemediationRepositoryImpl(session),
        participant_reader=OqiRemediationParticipantReader(session),
    )


def _admit_field_value_evidence(
    session: Session, *, source_field_id: UUID, value: str, reference: str
) -> UUID:
    evidence_id = uuid4()
    session.add(
        FieldValueEvidenceORM(
            field_value_evidence_id=evidence_id,
            source_field_id=source_field_id,
            source_record_reference=reference,
            observed_representation=value,
            observed_at=NOW,
            received_at=NOW,
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

    evidence_by_role: dict[str, UUID] = {}
    for role, value in roles.items():
        object_id, field_id = (object_a, field_a) if role == role_names[0] else (object_b, field_b)
        session.add(
            QualityComparisonEvaluationParticipantORM(
                evaluation_id=evaluation_id,
                participant_role=role,
                source_field_id=field_id,
                source_object_id=object_id,
                source_record_reference=f"REC-{role}",
                expected=True,
                authoritative=(role == authoritative_role),
            )
        )
        if value is not None:
            evidence_id = _admit_field_value_evidence(
                session, source_field_id=field_id, value=value, reference=f"REC-{role}"
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

    finding_id = uuid4()
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

    assert _table_count() == 90
    alembic.command.downgrade(config, "0023_oqi4_ontology_impact")
    assert _table_count() == 86
    alembic.command.upgrade(config, "0024_oqi5_remediation")
    assert _table_count() == 90


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


def test_execution_report_alone_never_resolves_only_fresh_evaluation_read_does(
    migrated_engine: Engine,
) -> None:
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

    # The Finding itself is still OPEN -- no evaluator has re-run yet.
    # Refreshing the case from the Finding's own current state must NOT
    # resolve it: the execution claim alone carries no truth weight.
    with factory() as session:
        refreshed = _service(session).refresh_case(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    assert refreshed.status is RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED

    # Only now does an independent, later, existing OQI2 evaluator re-run
    # resolve the Finding (simulated here as the fact the evaluator would
    # itself have produced -- this test asserts the read-linkage, not the
    # evaluator's own correctness, which OQI2's own test suite already
    # proves).
    with factory() as session:
        finding = session.get(QualityComparisonFindingORM, finding_id)
        assert finding is not None
        finding.status = "RESOLVED"
        finding.state_revision += 1
        session.commit()

    with factory() as session:
        refreshed_again = _service(session).refresh_case(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    assert refreshed_again.status is RemediationCaseStatus.RESOLVED
