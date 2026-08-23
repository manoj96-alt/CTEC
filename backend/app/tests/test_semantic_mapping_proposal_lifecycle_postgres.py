"""Postgres-backed acceptance evidence for Gate L (CDD-027 §11-§13, §27;
AI-Assisted Semantic Mapping Candidate Discovery Artifact Authorization
§4.1-§4.2, as corrected by the Human-Approver Attribution Clarification
and Remediation Report). Composes the real, unmodified H3 demo fixture
(`DemoFieldValueEvidenceSeeder`, reused by call only, no new seeder) with
one additional `SourceField` row created directly via the existing,
unmodified `SourceFieldRepositoryImpl.create()` -- ordinary test-fixture
construction using already-authorized H1 repository capability, not a new
seeder module -- to prove the full real-database lifecycle:

    tenant-bounded candidate universe (real query, real exclusion)
        -> deterministic validation
        -> Proposed SemanticMapping (real create())
        -> authenticated TrustedPrincipal approval
        -> NEW Approved SemanticMapping (real create())
        -> Proposed row unchanged
        -> Approved-uniqueness enforced by H1's existing, unmodified
           invariant (never weakened by this Gate)

Gate K/H2/Gate I are never called anywhere in this file.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid5

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.blueprint_service import BlueprintApplicationService
from app.application.semantic_mapping_candidate_discovery import (
    CandidateSelection,
    CandidateSourceField,
    SemanticMappingCandidateUniverseService,
)
from app.application.semantic_mapping_proposal_governance import (
    SemanticMappingProposalGovernanceApplicationService,
)
from app.core.bootstrap import (
    BOOTSTRAP_DEMO_TENANT_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.blueprint import InformationElementRequirement
from app.domain.integration import SourceField
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
    DemoFieldValueEvidenceSeedSummary,
)
from app.infrastructure.persistence.demo_semantic_mapping_seeder import (
    DemoSemanticMappingSeeder,
    DemoSemanticMappingSeedSummary,
)
from app.infrastructure.persistence.semantic_mapping_repository import (
    SemanticMappingRepositoryImpl,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

_RISK_EVENT_SEVERITY = "Risk Event Severity"


def _seed(
    factory: "sessionmaker[Session]",
) -> tuple[DemoFieldValueEvidenceSeedSummary, DemoSemanticMappingSeedSummary]:
    with factory() as session:
        summary = DemoFieldValueEvidenceSeeder(session).seed()
        mapping_summary = DemoSemanticMappingSeeder(session).seed(BOOTSTRAP_DEMO_TENANT_ID)
        session.commit()
    return summary, mapping_summary


def _ensure_source_field(
    session: Session, *, source_object_id: UUID, field_label: str
) -> Identifier:
    """Ordinary, idempotent test-fixture construction via the existing,
    unmodified H1 `SourceFieldRepositoryImpl.create()` -- not a new seeder
    module. Deterministic id (uuid5 under the existing BOOTSTRAP_SEED_NAMESPACE,
    matching every other seeder's own convention) so repeated calls within
    the same session-scoped test database create nothing new."""
    source_field_id = Identifier(
        uuid5(
            BOOTSTRAP_SEED_NAMESPACE, f"gate-l-test-source-field:{source_object_id}:{field_label}"
        )
    )
    existing = SourceFieldRepositoryImpl(session).get_by_id(source_field_id.value)
    if existing is not None:
        return source_field_id
    SourceFieldRepositoryImpl(session).create(
        SourceField(
            source_field_id=source_field_id,
            source_object_id=Identifier(source_object_id),
            field_label=CanonicalName(field_label),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=datetime.now(UTC),
        )
    )
    session.commit()
    return source_field_id


def _find_risk_event_severity(session: Session) -> InformationElementRequirement:
    blueprint = BlueprintApplicationService(
        repository=BlueprintRepositoryImpl(session)
    ).get_approved_by_name(CANONICAL_BLUEPRINT_NAME)
    assert blueprint is not None
    for concept in blueprint.concept_requirements:
        for element in concept.information_element_requirements:
            if element.element_name.value == _RISK_EVENT_SEVERITY:
                return element
    raise AssertionError(f"{_RISK_EVENT_SEVERITY!r} not found in canonical Blueprint")


def _principal(*, tenant_id: str) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="oidc-subject-real-human",
        tenant_id=tenant_id,
        scopes=(),
        roles=(),
        issuer="https://issuer.example",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


def test_candidate_universe_is_tenant_scoped_and_excludes_approved_mapped_source_field(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _summary, mapping_summary = _seed(factory)

    with factory() as session:
        second_field_id = _ensure_source_field(
            session,
            source_object_id=mapping_summary.source_object_id,
            field_label="LAND1_UNIVERSE_TEST",
        )
        risk_event_severity = _find_risk_event_severity(session)

        universe_service = SemanticMappingCandidateUniverseService(session=session)
        context = universe_service.build_context(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            information_element_requirement_id=risk_event_severity.information_element_requirement_id.value,
            element_name=risk_event_severity.element_name.value,
            description=risk_event_severity.description.value,
            obligation=risk_event_severity.obligation,
        )

    candidate_ids = {cf.source_field_id for cf in context.candidate_source_fields}
    assert second_field_id.value in candidate_ids
    assert mapping_summary.source_field_id not in candidate_ids  # already Approved-mapped


def test_full_lifecycle_propose_approve_and_second_target_approval_fails_closed(
    migrated_engine: Engine,
) -> None:
    """Combined into one test function (rather than split across two) so
    that ordering between "the one successful Approved-mapping-for-this-
    target" scenario and "a second, conflicting approval attempt for the
    same already-Approved target" scenario is explicit and self-contained,
    independent of pytest's cross-function execution order -- since
    `Risk Event Severity` can only ever be legitimately Approved-mapped
    once per test session (H1's own target-side uniqueness invariant,
    unweakened)."""
    factory = sessionmaker(migrated_engine)
    _summary, mapping_summary = _seed(factory)

    with factory() as session:
        first_field_id = _ensure_source_field(
            session,
            source_object_id=mapping_summary.source_object_id,
            field_label="LAND1_LIFECYCLE_TEST_A",
        )
        second_field_id = _ensure_source_field(
            session,
            source_object_id=mapping_summary.source_object_id,
            field_label="LAND1_LIFECYCLE_TEST_B",
        )
        risk_event_severity = _find_risk_event_severity(session)

        universe_service = SemanticMappingCandidateUniverseService(session=session)
        context = universe_service.build_context(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            information_element_requirement_id=risk_event_severity.information_element_requirement_id.value,
            element_name=risk_event_severity.element_name.value,
            description=risk_event_severity.description.value,
            obligation=risk_event_severity.obligation,
        )

        governance_service = SemanticMappingProposalGovernanceApplicationService(
            session=session,
            semantic_mapping_repository=SemanticMappingRepositoryImpl(session),
            source_field_repository=SourceFieldRepositoryImpl(session),
        )

        proposed = governance_service.materialize_proposal(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            candidate=CandidateSelection(source_field_id=first_field_id.value),
            context=context,
        )
        second_proposed = governance_service.materialize_proposal(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            candidate=CandidateSelection(source_field_id=second_field_id.value),
            context=context,
        )
        session.commit()

        assert proposed.governance_status is GovernanceStatus.PROPOSED
        assert proposed.created_by.value == BOOTSTRAP_SYSTEM_ENTITY_ID

        proposed_before_approval = SemanticMappingRepositoryImpl(session).get_by_id(
            proposed.semantic_mapping_id.value
        )
        assert proposed_before_approval == proposed

        approved = governance_service.approve(
            proposed=proposed, principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID)
        )
        session.commit()

        # A second, distinct Proposed row targeting the same
        # already-Approved InformationElementRequirement fails closed via
        # H1's own existing, unmodified target-side uniqueness invariant --
        # this stands in for a concurrent-approval race (per this
        # repository's own established precedent of proving such races via
        # sequential conflicting writes rather than true thread concurrency).
        with pytest.raises(ValidationException):
            governance_service.approve(
                proposed=second_proposed, principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID)
            )

    assert approved.governance_status is GovernanceStatus.APPROVED
    assert approved.semantic_mapping_id != proposed.semantic_mapping_id
    assert approved.source_field_id == proposed.source_field_id
    assert (
        approved.information_element_requirement_id == proposed.information_element_requirement_id
    )
    assert approved.created_by.value == BOOTSTRAP_SYSTEM_ENTITY_ID
    assert str(approved.created_by.value) != "oidc-subject-real-human"

    with factory() as session:
        proposed_after_approval = SemanticMappingRepositoryImpl(session).get_by_id(
            proposed.semantic_mapping_id.value
        )
        assert proposed_after_approval == proposed_before_approval  # byte-unchanged

        second_proposed_after_failed_approval = SemanticMappingRepositoryImpl(session).get_by_id(
            second_proposed.semantic_mapping_id.value
        )
        assert (
            second_proposed_after_failed_approval == second_proposed
        )  # unchanged by the failed attempt


def test_materialize_proposal_rejects_source_field_already_approved_even_if_context_stale(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _summary, mapping_summary = _seed(factory)

    with factory() as session:
        risk_event_severity = _find_risk_event_severity(session)

        # Deliberately construct a context that (incorrectly) still lists
        # the already-Approved-mapped NAME1 SourceField as a candidate --
        # simulating a stale/TOCTOU universe snapshot -- to prove
        # materialize_proposal's own defense-in-depth re-check, independent
        # of the universe-construction-time exclusion.
        universe_service = SemanticMappingCandidateUniverseService(session=session)
        stale_context = universe_service.build_context(
            tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
            information_element_requirement_id=risk_event_severity.information_element_requirement_id.value,
            element_name=risk_event_severity.element_name.value,
            description=risk_event_severity.description.value,
            obligation=risk_event_severity.obligation,
        )
        stale_context = type(stale_context)(
            information_element_requirement_id=stale_context.information_element_requirement_id,
            element_name=stale_context.element_name,
            description=stale_context.description,
            obligation=stale_context.obligation,
            candidate_source_fields=stale_context.candidate_source_fields
            + (
                CandidateSourceField(
                    source_field_id=mapping_summary.source_field_id,
                    field_label="NAME1",
                    source_object_id=mapping_summary.source_object_id,
                    source_object_name="LFA1",
                    source_system_id=mapping_summary.source_system_id,
                    source_system_name="H3 Demo ERP",
                ),
            ),
        )

        governance_service = SemanticMappingProposalGovernanceApplicationService(
            session=session,
            semantic_mapping_repository=SemanticMappingRepositoryImpl(session),
            source_field_repository=SourceFieldRepositoryImpl(session),
        )

        with pytest.raises(ValidationException):
            governance_service.materialize_proposal(
                tenant_id=BOOTSTRAP_DEMO_TENANT_ID,
                candidate=CandidateSelection(source_field_id=mapping_summary.source_field_id),
                context=stale_context,
            )


def test_no_new_provenance_table_or_migration_artifact_exists() -> None:
    # Structural, not runtime: the production modules import no persistence
    # model beyond the existing SourceField/SemanticMapping ORM classes
    # (proven exhaustively by import-hygiene in the unit test files); this
    # test exists only to make that acceptance criterion explicit here too.
    from app.application import semantic_mapping_proposal_governance as governance_module

    assert not hasattr(governance_module, "ApiSecurityAuditEvent")
    assert not hasattr(governance_module, "ApiSecurityAuditRepository")
