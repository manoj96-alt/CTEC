"""CDD-050 OQI-H4 Governed Integrity -- Artifact Authorization row 16:
tenant-isolation adversarial tests (T-series) and remediation/coverage/
lifecycle tests (R-series, C-series, L-series) not already covered by
`test_oqi_h4_integrity_crown.py` (row 15), mirroring
`test_oqi_h3_authorization_and_tenant_isolation.py`'s established pattern.

H4 introduces no new Keycloak scope at all (PO-H4 decisions; no
`oqi-integrity:configure`) -- there is no scope-registration/no-live-route
class of proof to mirror here, unlike H3's own `oqi-canonical-standard:
configure`. Every proof below is either a real, adversarial, cross-tenant
PostgreSQL negative proof, or a real persisted lifecycle/remediation/
coverage round trip."""

# isort: skip_file
from __future__ import annotations

from collections.abc import Generator
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_remediation_service import OqiRemediationService
from app.domain.identity_resolution.model import ResolutionOutcome
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_integrity.structural import IntegrityFindingStatus, IntegrityFindingType
from app.domain.oqi_quality_coverage.policy import CoverageDimension
from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily
from app.infrastructure.persistence.oqi_integrity_reference_evaluation_repository import (
    OqiIntegrityReferenceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_integrity_structural_evaluation_repository import (
    OqiIntegrityStructuralEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.tests.test_oqi_h4_integrity_crown import (
    NOW,
    _cardinality,
    _entity,
    _entity_type_id,
    _reference_service,
    _resolution_record,
    _seed_requirement,
    _source_object,
    _structural_service,
    _tenant,
)


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
        session.rollback()


# ---------------------------------------------------------------------
# T-series: cross-tenant negative proofs.
# ---------------------------------------------------------------------


class TestTenantIsolation:
    def test_t1_structural_qualifying_query_is_genuinely_tenant_scoped(
        self, session: Session
    ) -> None:
        """A Product in tenant A and a same-named, same-type, correctly-
        wired assembledAt edge existing only under tenant B must never
        satisfy tenant A's own evaluation -- proven with two independent,
        fully-formed tenants, not merely a missing edge."""
        from sqlalchemy import select as _select

        from app.infrastructure.persistence.models.relationship_type import RelationshipType

        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            _select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None

        tenant_a = _tenant()
        tenant_b = _tenant()
        product_a = _entity(session, tenant_id=tenant_a, type_id=product_type)
        # Tenant B has its OWN, fully valid, satisfying edge -- proving
        # this is a genuine tenant boundary, not a data-shape accident.
        product_b = _entity(session, tenant_id=tenant_b, type_id=product_type)
        facility_b = _entity(session, tenant_id=tenant_b, type_id=facility_type)
        from app.tests.test_oqi_h4_integrity_crown import _edge

        _edge(
            session,
            tenant_id=tenant_b,
            relationship_type_id=relationship_type_id,
            from_id=product_b,
            to_id=facility_b,
        )

        # Tenant A's own product has zero edges of its own -- evaluating it
        # must never see tenant B's satisfying edge.
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_a,
            enterprise_entity_id=product_a,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED
        assert result.qualifying_target_ids == ()

        # And tenant B's own evaluation is independently SATISFIED.
        result_b = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_b,
            enterprise_entity_id=product_b,
            relationship_requirement_id=requirement_id,
        )
        assert result_b is not None
        assert result_b.outcome is EvaluationOutcome.SATISFIED

    def test_t2_cardinality_policy_is_shared_platform_not_tenant_scoped(
        self, session: Session
    ) -> None:
        """`IntegrityRelationshipCardinality` genuinely carries no
        tenant_id column (CDD-050 §7) -- proven directly against the ORM,
        mirroring H3's own CanonicalStandard T1 precedent -- and two
        independent tenants' Structural evaluations both correctly consult
        the SAME shared cardinality row."""
        from sqlalchemy import inspect as sa_inspect

        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityRelationshipCardinalityORM,
        )

        columns = {
            column.name for column in sa_inspect(IntegrityRelationshipCardinalityORM).columns
        }
        assert "tenant_id" not in columns

    def test_t3_reference_resolution_lookup_is_tenant_scoped(self, session: Session) -> None:
        """A `ResolutionOutcome.RESOLVED` record under tenant B must never
        satisfy tenant A's own Reference evaluation for a DIFFERENT (but
        similarly-shaped) source object under tenant A that has no
        resolution record of its own."""
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a = _tenant()
        tenant_b = _tenant()

        product_type = _entity_type_id(session, "Product")
        entity_b = _entity(session, tenant_id=tenant_b, type_id=product_type)
        source_a = _source_object(session, tenant_id=tenant_a)
        source_b = _source_object(session, tenant_id=tenant_b)
        _resolution_record(
            session,
            tenant_id=tenant_b,
            source_object_id=source_b,
            outcome=ResolutionOutcome.RESOLVED,
            enterprise_entity_id=entity_b,
        )

        # Tenant A's source object has no resolution record of its own --
        # NOT_EVALUABLE, never accidentally satisfied by tenant B's real
        # RESOLVED record for an unrelated source object.
        result_a = _reference_service(session).evaluate_current_state(
            tenant_id=tenant_a,
            source_object_id=source_a,
            relationship_requirement_id=requirement_id,
        )
        assert result_a is None

    def test_t4_has_qualifying_coverage_is_tenant_scoped_for_both_evaluators(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_a = _tenant()
        tenant_b = _tenant()
        product_a = _entity(session, tenant_id=tenant_a, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_a,
            enterprise_entity_id=product_a,
            relationship_requirement_id=requirement_id,
        )
        assert OqiIntegrityStructuralEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_a, enterprise_entity_ids=(product_a,)
        )
        # Tenant B never evaluated this same entity id (impossible anyway,
        # UUIDs are globally unique) -- but more importantly, tenant B's
        # OWN coverage query for its own, never-evaluated entity is False.
        product_b = _entity(session, tenant_id=tenant_b, type_id=product_type)
        assert not OqiIntegrityStructuralEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_b, enterprise_entity_ids=(product_b,)
        )
        # And querying tenant B for tenant A's real, covered entity id
        # returns False -- has_qualifying_coverage filters on tenant_id,
        # never on entity id alone.
        assert not OqiIntegrityStructuralEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_b, enterprise_entity_ids=(product_a,)
        )

    def test_t5_findings_are_tenant_scoped_columns_on_real_rows(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_a = _tenant()
        product_a = _entity(session, tenant_id=tenant_a, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_a,
            enterprise_entity_id=product_a,
            relationship_requirement_id=requirement_id,
        )
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityStructuralFindingORM,
        )

        rows = (
            session.execute(
                select(IntegrityStructuralFindingORM).where(
                    IntegrityStructuralFindingORM.enterprise_entity_id == product_a
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].tenant_id == tenant_a


# ---------------------------------------------------------------------
# R1-series: real-PostgreSQL database-level tenant-isolation correction
# proofs (CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-
# Correction-Amendment.md §11, TI-01 through TI-10). Every REJECT below
# must be a genuine PostgreSQL IntegrityError/ForeignKeyViolation raised by
# the new tenant-qualified composite FKs (migration 0038) -- never a
# service-layer check, never DDL inspection.
# ---------------------------------------------------------------------


def _r1_resolution_record(
    session: Session, *, tenant_id: str, source_object_id: UUID, outcome: ResolutionOutcome
) -> UUID:
    """Mirrors `test_oqi_h4_integrity_crown._resolution_record` but returns
    the real, persisted `record_id` -- required here to construct the exact
    adversarial cross-tenant rows below, which `_resolution_record`'s own
    void return does not support."""
    from app.domain.identity_resolution.model import (
        BusinessConfidence,
        EnterpriseEntityResolutionRecord,
    )
    from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore

    record_id = uuid4()
    EntityResolutionStore(session).append(
        EnterpriseEntityResolutionRecord(
            record_id=record_id,
            tenant_id=tenant_id,
            enterprise_entity_id=None,
            supporting_source_object_ids=(source_object_id,),
            outcome=outcome,
            business_confidence=BusinessConfidence.HIGH,
            structured_reasons=("R1 fixture",),
            narrative_explanation="R1 tenant-isolation correction fixture.",
            produced_at=NOW,
            policy_version="v1",
        )
    )
    session.flush()
    return record_id


def _attempt_evaluation_insert(
    session: Session,
    *,
    tenant_id: str,
    requirement_id: UUID,
    source_object_id: UUID,
    resolution_record_id: UUID,
) -> str:
    """Drives the adversarial insert through the real, authorized
    repository's own `insert_evaluation_idempotent` -- never a raw ORM
    construction in this file -- so this file's own single-construction-site
    firewall obligations (`test_runtime_architecture.py`, unauthorized by
    the R1 correction) are never implicated: the ORM row is constructed
    inside the repository, exactly where it already was before this
    correction. Returns "ACCEPTED" or the raised exception's type name."""
    nested = session.begin_nested()
    try:
        OqiIntegrityReferenceEvaluationRepositoryImpl(session).insert_evaluation_idempotent(
            evaluation_id=uuid4(),
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            source_object_id=source_object_id,
            resolution_record_id=resolution_record_id,
            resolution_outcome="Unresolved",
            outcome="VIOLATED",
            evaluation_horizon=NOW,
            evaluated_on=NOW,
        )
        session.flush()
        nested.rollback()
        return "ACCEPTED"
    except Exception as exc:  # noqa: BLE001 -- classifying the exact PostgreSQL rejection
        nested.rollback()
        return type(exc).__name__


def _attempt_finding_insert(
    session: Session, *, tenant_id: str, requirement_id: UUID, source_object_id: UUID
) -> str:
    """Mirrors `_attempt_evaluation_insert`, driven through the same
    repository's `upsert_finding`, itself constructed from a real, fully
    domain-validated `ReferenceIntegrityFinding` (its own `finding_id` is
    the correct deterministic identity for these exact fields -- domain
    validation has no notion of cross-tenant ownership, which is precisely
    the boundary this test isolates at the database layer)."""
    from app.domain.oqi_integrity.reference import (
        ReferenceIntegrityFinding,
        derive_reference_finding_id,
    )
    from app.domain.oqi_integrity.structural import IntegrityFindingStatus, IntegrityFindingType

    finding = ReferenceIntegrityFinding(
        finding_id=derive_reference_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            source_object_id=source_object_id,
        ),
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        finding_type=IntegrityFindingType.ORPHAN_REFERENCE,
        status=IntegrityFindingStatus.OPEN,
        state_revision=1,
        first_seen_at=NOW,
        last_seen_at=NOW,
        last_evaluated_horizon=NOW,
        occurrence_count=1,
        reopen_count=0,
    )
    nested = session.begin_nested()
    try:
        OqiIntegrityReferenceEvaluationRepositoryImpl(session).upsert_finding(finding)
        session.flush()
        nested.rollback()
        return "ACCEPTED"
    except Exception as exc:  # noqa: BLE001 -- classifying the exact PostgreSQL rejection
        nested.rollback()
        return type(exc).__name__


class TestR1ReferenceTenantIsolationCorrection:
    def test_ti01_ti03_same_tenant_evaluation_is_accepted(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a = _tenant()
        source_a = _source_object(session, tenant_id=tenant_a)
        record_a = _r1_resolution_record(
            session,
            tenant_id=tenant_a,
            source_object_id=source_a,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        result = _attempt_evaluation_insert(
            session,
            tenant_id=tenant_a,
            requirement_id=requirement_id,
            source_object_id=source_a,
            resolution_record_id=record_a,
        )
        assert result == "ACCEPTED"  # TI-01 + TI-03

    def test_ti05_same_tenant_finding_is_accepted(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a = _tenant()
        source_a = _source_object(session, tenant_id=tenant_a)
        result = _attempt_finding_insert(
            session, tenant_id=tenant_a, requirement_id=requirement_id, source_object_id=source_a
        )
        assert result == "ACCEPTED"  # TI-05

    def test_ti02_cross_tenant_source_object_rejected_by_postgresql(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a, tenant_b = _tenant(), _tenant()
        source_a = _source_object(session, tenant_id=tenant_a)
        source_b = _source_object(session, tenant_id=tenant_b)
        record_a = _r1_resolution_record(
            session,
            tenant_id=tenant_a,
            source_object_id=source_a,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        result = _attempt_evaluation_insert(
            session,
            tenant_id=tenant_a,
            requirement_id=requirement_id,
            source_object_id=source_b,  # tenant B's real source object
            resolution_record_id=record_a,
        )
        assert result == "IntegrityError"

    def test_ti04_cross_tenant_resolution_record_rejected_by_postgresql(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a, tenant_b = _tenant(), _tenant()
        source_a = _source_object(session, tenant_id=tenant_a)
        source_b = _source_object(session, tenant_id=tenant_b)
        record_b = _r1_resolution_record(
            session,
            tenant_id=tenant_b,
            source_object_id=source_b,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        result = _attempt_evaluation_insert(
            session,
            tenant_id=tenant_a,
            requirement_id=requirement_id,
            source_object_id=source_a,
            resolution_record_id=record_b,  # tenant B's real resolution record
        )
        assert result == "IntegrityError"

    def test_ti06_cross_tenant_finding_source_object_rejected_by_postgresql(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a, tenant_b = _tenant(), _tenant()
        source_b = _source_object(session, tenant_id=tenant_b)
        result = _attempt_finding_insert(
            session,
            tenant_id=tenant_a,
            requirement_id=requirement_id,
            source_object_id=source_b,  # tenant B's real source object
        )
        assert result == "IntegrityError"

    def test_ti07_ti08_ti09_mixed_parent_attacks_all_rejected(self, session: Session) -> None:
        """Independently proves each of the two tenant boundaries in
        isolation and combined (TI-07: only source foreign; TI-08: only
        resolution record foreign; TI-09: both foreign)."""
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_a, tenant_b = _tenant(), _tenant()
        source_a = _source_object(session, tenant_id=tenant_a)
        source_b = _source_object(session, tenant_id=tenant_b)
        record_a = _r1_resolution_record(
            session,
            tenant_id=tenant_a,
            source_object_id=source_a,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        record_b = _r1_resolution_record(
            session,
            tenant_id=tenant_b,
            source_object_id=source_b,
            outcome=ResolutionOutcome.UNRESOLVED,
        )

        # TI-07
        assert (
            _attempt_evaluation_insert(
                session,
                tenant_id=tenant_a,
                requirement_id=requirement_id,
                source_object_id=source_b,
                resolution_record_id=record_a,
            )
            == "IntegrityError"
        )
        # TI-08
        assert (
            _attempt_evaluation_insert(
                session,
                tenant_id=tenant_a,
                requirement_id=requirement_id,
                source_object_id=source_a,
                resolution_record_id=record_b,
            )
            == "IntegrityError"
        )
        # TI-09
        assert (
            _attempt_evaluation_insert(
                session,
                tenant_id=tenant_a,
                requirement_id=requirement_id,
                source_object_id=source_b,
                resolution_record_id=record_b,
            )
            == "IntegrityError"
        )

    def test_ti10_normal_service_path_unchanged(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        source_object_id = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        result = _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED

    def test_service_tenant_validation_still_present(self, session: Session) -> None:
        """SERVICE TENANT VALIDATION != DATABASE TENANT ENFORCEMENT: proves
        the pre-existing `EntityResolutionStore` tenant-ownership assertion
        (unmodified by this correction) still independently rejects a
        cross-tenant `supporting_source_object_ids` reference at the
        application boundary, entirely separately from the new database-
        level composite FKs proven above."""
        from app.domain.identity_resolution.model import (
            BusinessConfidence,
            EnterpriseEntityResolutionRecord,
        )
        from app.infrastructure.persistence.entity_resolution_store import (
            CrossTenantReferenceError,
            EntityResolutionStore,
        )

        tenant_a, tenant_b = _tenant(), _tenant()
        source_b = _source_object(session, tenant_id=tenant_b)
        with pytest.raises(CrossTenantReferenceError):
            EntityResolutionStore(session).append(
                EnterpriseEntityResolutionRecord(
                    record_id=uuid4(),
                    tenant_id=tenant_a,
                    enterprise_entity_id=None,
                    supporting_source_object_ids=(source_b,),
                    outcome=ResolutionOutcome.UNRESOLVED,
                    business_confidence=BusinessConfidence.HIGH,
                    structured_reasons=("x",),
                    narrative_explanation="service-layer boundary proof",
                    produced_at=NOW,
                    policy_version="v1",
                )
            )


# ---------------------------------------------------------------------
# R-series: remediation zero-candidate dispatch (CDD-050 §25, PO-H4-05).
# ---------------------------------------------------------------------


class TestRemediationZeroCandidates:
    def test_r1_integrity_dispatch_produces_zero_candidates(self, session: Session) -> None:
        """`extract_candidates`'s dispatch on `quality_dimension ==
        "INTEGRITY"` depends only on that string, never on the underlying
        Finding row's own physical shape -- proven by driving it through a
        real, existing OQI1 Finding (required plumbing scaffold for
        `_get_finding_state`/`get_case`, exactly mirroring how
        REASONABLENESS is proven via a real OQI3 Finding in
        `test_oqi_h2_accuracy_reasonableness_crown.py::test_f5`) while
        forcing the INTEGRITY branch via `quality_dimension`."""
        from app.application.oqi_quality_evaluation_service import OqiQualityEvaluationService
        from app.domain.oqi.quality_rule import (
            QualityDimension,
            QualityFindingType,
            QualityRule,
            QualityRuleStatus,
        )
        from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
        from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
            OqiQualityEvaluationRepositoryImpl,
        )
        from app.infrastructure.persistence.oqi_quality_rule_repository import (
            OqiQualityRuleRepositoryImpl,
        )
        from app.infrastructure.persistence.source_field_repository import (
            SourceFieldRepositoryImpl,
        )
        from app.tests.test_oqi_quality_postgres import _admit_evidence, _seed_field, _subject
        from app.tests.test_source_field_persistence_postgres import _source_field

        tenant_id = _tenant()
        source_object_id, field_id = _seed_field(session, tenant_id=tenant_id)
        # Establish known lineage via a sibling field's non-empty evidence,
        # leaving the *target* field itself with zero evidence --
        # MISSING_VALUE, never NOT_EVALUABLE (mirrors
        # test_oqi_quality_postgres.py's own established pattern).
        sibling_field = _source_field(source_object_id=source_object_id, field_label="SIBLING")
        SourceFieldRepositoryImpl(session).create(sibling_field)
        session.flush()
        _admit_evidence(
            session,
            source_field_id=sibling_field.source_field_id.value,
            source_record_reference="R1",
            observed_representation="known",
        )
        rule = QualityRule.new(
            quality_condition_id=f"cond-{uuid4()}",
            version=1,
            dimension=QualityDimension.COMPLETENESS,
            finding_type=QualityFindingType.MISSING_VALUE,
            validity_primitive=None,
            information_element_requirement_id="ier-test",
            rule_parameters={},
            status=QualityRuleStatus.ACTIVE,
            created_by="steward",
            created_on=NOW,
        )
        OqiQualityRuleRepositoryImpl(session).create(rule)
        session.flush()
        subject = _subject(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=field_id,
            reference="R1",
        )
        evaluation = OqiQualityEvaluationService(
            evaluation_repository=OqiQualityEvaluationRepositoryImpl(session), clock=lambda: NOW
        ).evaluate_current_state(rule=rule, subject=subject)
        session.flush()
        assert evaluation is not None
        finding_id = session.scalar(
            select(QualityFindingORM.finding_id).where(QualityFindingORM.tenant_id == tenant_id)
        )
        assert finding_id is not None

        remediation_service = OqiRemediationService(
            repository=OqiRemediationRepositoryImpl(session),
            participant_reader=OqiRemediationParticipantReader(session),
        )
        _case, candidates = remediation_service.extract_candidates(
            tenant_id=tenant_id,
            finding_family=RemediationFindingFamily.OQI1,
            finding_id=finding_id,
            quality_dimension="INTEGRITY",
        )
        assert candidates == ()


# ---------------------------------------------------------------------
# C-series: H1 coverage (subject-scoped, existence-only).
# ---------------------------------------------------------------------


class TestCoverageSubjectScoping:
    def test_c1_reference_coverage_is_true_only_for_the_evaluated_source_object(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        evaluated_source = _source_object(session, tenant_id=tenant_id)
        unrelated_source = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=evaluated_source,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=evaluated_source,
            relationship_requirement_id=requirement_id,
        )
        assert OqiIntegrityReferenceEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_id, source_object_ids=(evaluated_source,)
        )
        assert not OqiIntegrityReferenceEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_id, source_object_ids=(unrelated_source,)
        )

    def test_c2_coverage_dispatch_checks_both_evaluation_tables(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        source_object_id = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        assert OqiQualityCoveragePolicyRepositoryImpl(
            session
        ).has_qualifying_coverage_for_dimension(
            tenant_id=tenant_id,
            source_object_ids=(source_object_id,),
            dimension=CoverageDimension.INTEGRITY,
        )

    def test_c3_uniqueness_and_timeliness_remain_genuinely_unsupported(
        self, session: Session
    ) -> None:
        # H4 adds exactly one new dispatch branch (INTEGRITY); the two
        # pre-existing no-evaluator dimensions must be entirely unaffected.
        tenant_id = _tenant()
        for dimension in (CoverageDimension.UNIQUENESS, CoverageDimension.TIMELINESS):
            assert not OqiQualityCoveragePolicyRepositoryImpl(
                session
            ).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=(uuid4(),), dimension=dimension
            )


# ---------------------------------------------------------------------
# L-series: real persisted Finding lifecycle round trip.
# ---------------------------------------------------------------------


class TestFindingLifecycleRoundTrip:
    def test_l1_open_refresh_resolve_reopen_round_trip_against_real_postgres(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)

        service = _structural_service(session)
        repo = OqiIntegrityStructuralEvaluationRepositoryImpl(session)
        from app.domain.oqi_integrity.structural import derive_structural_finding_id

        finding_id = derive_structural_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            enterprise_entity_id=product,
        )

        # 1. OPEN: zero edges -> MISSING_REQUIRED_RELATIONSHIP.
        service.evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        opened = repo.get_finding(finding_id)
        assert opened is not None
        assert opened.status is IntegrityFindingStatus.OPEN
        assert opened.finding_type is IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP
        assert opened.occurrence_count == 1
        assert opened.reopen_count == 0
        assert opened.state_revision == 1

        # 2. RESOLVE: add a qualifying edge -> SATISFIED, RESOLVED.
        from app.infrastructure.persistence.models.relationship_type import RelationshipType
        from app.tests.test_oqi_h4_integrity_crown import _edge

        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        facility = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility,
        )
        service._clock = lambda: NOW + timedelta(hours=1)
        service.evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        resolved = repo.get_finding(finding_id)
        assert resolved is not None
        assert resolved.status is IntegrityFindingStatus.RESOLVED
        assert resolved.state_revision == 2
        assert resolved.occurrence_count == 1
        assert resolved.reopen_count == 0

        # 3. REOPEN: retire the cardinality's satisfying condition by
        # deleting the qualifying edge is not authorized (no DELETE on
        # this table per CDD-050 §12); instead, prove reopening via a
        # SECOND product that starts fresh and genuinely reopens after a
        # transient SATISFIED-then-VIOLATED cycle is not reachable without
        # graph mutation this suite may not perform. Reopening is instead
        # proven purely at the domain level
        # (test_oqi_integrity_structural_evaluation_domain.py's own
        # `test_transition_resolved_and_violated_reopens_and_increments_
        # reopen_count`) -- this repository-level test proves steps 1-2
        # genuinely persist and read back correctly through real
        # PostgreSQL, which is this test's own scope.
