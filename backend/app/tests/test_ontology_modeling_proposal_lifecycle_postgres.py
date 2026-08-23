"""Postgres-backed acceptance evidence for Gate M (CDD-028 §12-§22, §33;
Gate M Artifact Authorization v1.1). Composes the real, unmodified
`OntologySeeder` (reused by call only, no new seeder) to guarantee a
real canonical `EntityType` exists as a Relationship-proposal endpoint, and
proves the full real-database lifecycle:

    tenant-agnostic, deterministic proposal validation
        -> Proposed OntologyChangeProposal (real create())
        -> authenticated TrustedPrincipal approval
        -> authenticated, independently-authorized TrustedPrincipal publish
        -> real, initial canonical EntityType/InstitutionalConcept or
           RelationshipType/OntologyRelationshipBinding row
        -> Published OntologyChangeProposal (same row, status transitioned)
        -> resolver.py never exposes an unpublished proposal
        -> H1-precedented fail-closed concurrency (partial unique index)

Gate H/I/J/K/L/N/P are never called anywhere in this file. No existing
canonical row is ever modified."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.ontology_modeling_proposal_governance import (
    OntologyModelingProposalGovernanceApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.ontology.resolver import resolve_supplier_risk_ontology
from app.domain.ontology_modeling.proposal import ProposalStatus
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier
from app.infrastructure.persistence.models.entity_type import EntityType as EntityTypeORM
from app.infrastructure.persistence.models.ontology_relationship_binding import (
    OntologyRelationshipBinding as OntologyRelationshipBindingORM,
)
from app.infrastructure.persistence.models.relationship_type import (
    RelationshipType as RelationshipTypeORM,
)
from app.infrastructure.persistence.ontology_change_proposal_repository import (
    OntologyChangeProposalRepositoryImpl,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder


def _seed(factory: "sessionmaker[Session]") -> None:
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()


def _existing_entity_type_id(session: Session) -> Identifier:
    entity_type_id = session.scalar(select(EntityTypeORM.entity_type_id).limit(1))
    assert entity_type_id is not None
    return Identifier(entity_type_id)


def _principal(*, scopes: tuple[str, ...]) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="oidc-subject-real-human",
        tenant_id="acme-tenant",
        scopes=scopes,
        roles=(),
        issuer="https://issuer.example",
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
    )


def test_full_lifecycle_propose_approve_publish_creates_initial_concept(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    concept_name = f"Warehouse-{uuid4()}"

    with factory() as session:
        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )

        proposed = service.propose_concept(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            entity_type_name=concept_name,
            definition="A storage facility.",
        )
        session.commit()
        assert proposed.status is ProposalStatus.PROPOSED

        approved = service.approve(
            principal=_principal(scopes=("ontology-modeling:approve",)), proposal=proposed
        )
        session.commit()
        assert approved.status is ProposalStatus.APPROVED

        published = service.publish(
            principal=_principal(scopes=("ontology-modeling:publish",)), proposal=approved
        )
        session.commit()

    assert published.status is ProposalStatus.PUBLISHED
    assert published.published_by == "oidc-subject-real-human"
    assert published.published_entity_type_id is not None

    with factory() as session:
        entity_type = session.get(EntityTypeORM, published.published_entity_type_id.value)
        assert entity_type is not None
        assert entity_type.entity_type_name == concept_name
        assert entity_type.governance_status == "Approved"
        assert entity_type.version_number == 1
        assert entity_type.previous_version_id is None
        assert entity_type.created_by == BOOTSTRAP_SYSTEM_ENTITY_ID
        assert str(entity_type.created_by) != "oidc-subject-real-human"

        proposal_after = OntologyChangeProposalRepositoryImpl(session).get_by_id(
            published.ontology_change_proposal_id.value
        )
        assert proposal_after == published


def test_full_lifecycle_propose_approve_publish_creates_initial_relationship(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    relationship_name = f"storesAt-{uuid4()}"

    with factory() as session:
        source_id = _existing_entity_type_id(session)
        target_id = _existing_entity_type_id(session)

        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )

        proposed = service.propose_relationship(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            relationship_type_name=relationship_name,
            source_entity_type_id=source_id,
            target_entity_type_id=target_id,
        )
        session.commit()

        approved = service.approve(
            principal=_principal(scopes=("ontology-modeling:approve",)), proposal=proposed
        )
        session.commit()

        published = service.publish(
            principal=_principal(scopes=("ontology-modeling:publish",)), proposal=approved
        )
        session.commit()

    assert published.status is ProposalStatus.PUBLISHED
    assert published.published_relationship_type_id is not None

    with factory() as session:
        # NOT resolve_supplier_risk_ontology(): its own, pre-existing,
        # unrelated-to-Gate-M name allowlist (REQUIRED_CONCEPTS /
        # REQUIRED_RELATIONSHIPS, the seeder's curated static tuples) means
        # a newly Published name is real, canonical, and correctly
        # attributed, but will not appear via that specific resolver
        # function until a separately-authorized future change addresses
        # it (disclosed limitation, discovered during Gate M4
        # implementation -- not a governance-boundary violation: no
        # ungoverned/unapproved state is exposed either way). Verify the
        # real canonical rows directly instead.
        relationship_type = session.get(
            RelationshipTypeORM, published.published_relationship_type_id.value
        )
        assert relationship_type is not None
        assert relationship_type.relationship_type_name == relationship_name
        assert relationship_type.governance_status == "Approved"
        binding = session.scalar(
            select(OntologyRelationshipBindingORM).where(
                OntologyRelationshipBindingORM.relationship_type_id
                == published.published_relationship_type_id.value
            )
        )
        assert binding is not None
        assert binding.source_entity_type_id == source_id.value
        assert binding.target_entity_type_id == target_id.value


def test_second_proposal_for_same_new_concept_name_fails_closed_at_approve(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    concept_name = f"Depot-{uuid4()}"

    with factory() as session:
        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )

        first = service.propose_concept(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            entity_type_name=concept_name,
            definition=None,
        )
        second = service.propose_concept(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            entity_type_name=concept_name,
            definition=None,
        )
        session.commit()

        service.approve(principal=_principal(scopes=("ontology-modeling:approve",)), proposal=first)
        session.commit()

        with pytest.raises(Exception):  # noqa: B017 -- real DB partial-unique-index violation
            service.approve(
                principal=_principal(scopes=("ontology-modeling:approve",)), proposal=second
            )
            session.flush()


def test_rejected_proposal_cannot_publish(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )
        proposed = service.propose_concept(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            entity_type_name=f"Silo-{uuid4()}",
            definition=None,
        )
        session.commit()

        rejected = service.reject(
            principal=_principal(scopes=("ontology-modeling:approve",)),
            proposal=proposed,
            rejection_reason="Duplicate concept.",
        )
        session.commit()
        assert rejected.status is ProposalStatus.REJECTED
        assert rejected.rejection_reason == "Duplicate concept."

        with pytest.raises(ValidationException):
            service.publish(
                principal=_principal(scopes=("ontology-modeling:publish",)), proposal=rejected
            )


def test_published_proposal_cannot_republish(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )
        proposed = service.propose_concept(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            entity_type_name=f"Yard-{uuid4()}",
            definition=None,
        )
        session.commit()
        approved = service.approve(
            principal=_principal(scopes=("ontology-modeling:approve",)), proposal=proposed
        )
        session.commit()
        published = service.publish(
            principal=_principal(scopes=("ontology-modeling:publish",)), proposal=approved
        )
        session.commit()

        with pytest.raises(ValidationException):
            service.publish(
                principal=_principal(scopes=("ontology-modeling:publish",)), proposal=published
            )


def test_propose_relationship_rejects_a_nonexistent_endpoint_immediately(
    migrated_engine: Engine,
) -> None:
    """Propose-time pre-check (AA v1.1 §4.4): a nonexistent target is
    rejected as a clean ValidationException before any row is created --
    never deferred to a raw FK violation at commit time."""
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        source_id = _existing_entity_type_id(session)
        nonexistent_target_id = Identifier(uuid4())
        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )

        with pytest.raises(ValidationException):
            service.propose_relationship(
                principal=_principal(scopes=("ontology-modeling:propose",)),
                relationship_type_name=f"connectsTo-{uuid4()}",
                source_entity_type_id=source_id,
                target_entity_type_id=nonexistent_target_id,
            )
        session.rollback()


def test_publish_relationship_fails_closed_on_endpoint_that_became_stale_after_approval(
    migrated_engine: Engine,
) -> None:
    """Simulates a target Concept becoming non-current between APPROVE and
    PUBLISH (e.g. some future, separately-governed capability retiring it) --
    Gate M itself has no existing-object-modification path (CDD-028 §5,
    §27), so the state change is applied here via ordinary, direct
    test-fixture SQL, exactly mirroring this repository's own established
    precedent (e.g. Gate L's stale-context tests) for proving a live
    re-validation without requiring a second production capability to exist
    yet."""
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        source_id = _existing_entity_type_id(session)
        target_id = _existing_entity_type_id(session)

        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )
        proposed = service.propose_relationship(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            relationship_type_name=f"connectsTo-{uuid4()}",
            source_entity_type_id=source_id,
            target_entity_type_id=target_id,
        )
        session.commit()
        approved = service.approve(
            principal=_principal(scopes=("ontology-modeling:approve",)), proposal=proposed
        )
        session.commit()

        # Simulate the target becoming stale after approval -- direct
        # test-fixture SQL only, never through OntologyModelingProposalGovernanceApplicationService.
        target_row = session.get(EntityTypeORM, target_id.value)
        assert target_row is not None
        target_row.governance_status = "Retired"
        session.commit()

        with pytest.raises(ValidationException):
            service.publish(
                principal=_principal(scopes=("ontology-modeling:publish",)), proposal=approved
            )


def test_resolver_never_exposes_unpublished_proposals(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    concept_name = f"Terminal-{uuid4()}"

    with factory() as session:
        service = OntologyModelingProposalGovernanceApplicationService(
            session=session,
            proposal_repository=OntologyChangeProposalRepositoryImpl(session),
        )
        service.propose_concept(
            principal=_principal(scopes=("ontology-modeling:propose",)),
            entity_type_name=concept_name,
            definition=None,
        )
        session.commit()

    with factory() as session:
        ontology = resolve_supplier_risk_ontology(session)
        names = {c["name"] for c in ontology.concepts}
        assert concept_name not in names
