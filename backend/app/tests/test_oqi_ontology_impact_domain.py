"""CDD-042 domain-layer tests: identity formulas, validation, and the
Finding-family adapter reference. Artifact Authorization §2 row 10."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    CurrentOntologyImpact,
    FindingFamily,
    FindingReference,
    ImpactBasis,
    ImpactClass,
    ImpactOutcome,
    OntologyElementType,
    OntologyImpactEvaluation,
    OntologyImpactObservation,
    OntologyImpactPath,
    compute_traversed_state_digest,
    derive_current_ontology_impact_id,
    derive_ontology_impact_evaluation_id,
)
from app.domain.oqi_ontology_impact.policy import (
    GLOBAL_MAX_DEPTH_CEILING,
    ImpactPropagationPolicy,
    PolicyGovernanceStatus,
    PropagationDirection,
)
from app.domain.shared.exceptions import ValidationException

TENANT = "tenant-a"


def _direct_observation(entity_id: UUID) -> OntologyImpactObservation:
    return OntologyImpactObservation(
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=entity_id,
        impact_kind=ImpactClass.DIRECT,
        basis=ImpactBasis.DIRECT_ENTITY_IDENTITY_LINEAGE,
        depth=0,
    )


class TestFindingReference:
    def test_valid_reference(self) -> None:
        ref = FindingReference(
            finding_family=FindingFamily.OQI1, finding_id=uuid4(), finding_state_revision=1
        )
        assert ref.finding_family is FindingFamily.OQI1

    def test_rejects_non_positive_revision(self) -> None:
        with pytest.raises(ValidationException):
            FindingReference(
                finding_family=FindingFamily.OQI2, finding_id=uuid4(), finding_state_revision=0
            )


class TestImpactPropagationPolicy:
    def test_valid_first_version(self) -> None:
        policy = ImpactPropagationPolicy(
            policy_id=uuid4(),
            tenant_id=TENANT,
            relationship_type_id=uuid4(),
            direction=PropagationDirection.FORWARD,
            max_depth=3,
            governance_status=PolicyGovernanceStatus.ACTIVE,
            version_number=1,
            previous_version_id=None,
        )
        assert policy.max_depth == 3

    def test_rejects_depth_above_global_ceiling(self) -> None:
        with pytest.raises(ValidationException):
            ImpactPropagationPolicy(
                policy_id=uuid4(),
                tenant_id=TENANT,
                relationship_type_id=uuid4(),
                direction=PropagationDirection.BOTH,
                max_depth=GLOBAL_MAX_DEPTH_CEILING + 1,
                governance_status=PolicyGovernanceStatus.ACTIVE,
                version_number=1,
                previous_version_id=None,
            )

    def test_rejects_zero_depth(self) -> None:
        with pytest.raises(ValidationException):
            ImpactPropagationPolicy(
                policy_id=uuid4(),
                tenant_id=TENANT,
                relationship_type_id=uuid4(),
                direction=PropagationDirection.BOTH,
                max_depth=0,
                governance_status=PolicyGovernanceStatus.ACTIVE,
                version_number=1,
                previous_version_id=None,
            )

    def test_version_one_must_not_carry_previous(self) -> None:
        with pytest.raises(ValidationException):
            ImpactPropagationPolicy(
                policy_id=uuid4(),
                tenant_id=TENANT,
                relationship_type_id=uuid4(),
                direction=PropagationDirection.BOTH,
                max_depth=1,
                governance_status=PolicyGovernanceStatus.ACTIVE,
                version_number=1,
                previous_version_id=uuid4(),
            )

    def test_version_two_must_carry_previous(self) -> None:
        with pytest.raises(ValidationException):
            ImpactPropagationPolicy(
                policy_id=uuid4(),
                tenant_id=TENANT,
                relationship_type_id=uuid4(),
                direction=PropagationDirection.BOTH,
                max_depth=1,
                governance_status=PolicyGovernanceStatus.ACTIVE,
                version_number=2,
                previous_version_id=None,
            )


class TestTraversedStateDigest:
    def test_order_invariant(self) -> None:
        rel_a, rel_b = uuid4(), uuid4()
        policy_a = uuid4()
        digest_1 = compute_traversed_state_digest(
            resolution_record_id=None,
            resolution_outcome="IMPACTED",
            traversed_relationships=((rel_a, 1), (rel_b, 1)),
            applied_policies=((policy_a, 1),),
        )
        digest_2 = compute_traversed_state_digest(
            resolution_record_id=None,
            resolution_outcome="IMPACTED",
            traversed_relationships=((rel_b, 1), (rel_a, 1)),
            applied_policies=((policy_a, 1),),
        )
        assert digest_1 == digest_2

    def test_version_sensitive(self) -> None:
        rel_a = uuid4()
        digest_1 = compute_traversed_state_digest(
            resolution_record_id=None,
            resolution_outcome="IMPACTED",
            traversed_relationships=((rel_a, 1),),
            applied_policies=(),
        )
        digest_2 = compute_traversed_state_digest(
            resolution_record_id=None,
            resolution_outcome="IMPACTED",
            traversed_relationships=((rel_a, 2),),
            applied_policies=(),
        )
        assert digest_1 != digest_2


class TestOntologyImpactEvaluation:
    def _build(
        self,
        *,
        outcome: ImpactOutcome,
        observations: tuple[OntologyImpactObservation, ...] = (),
    ) -> OntologyImpactEvaluation:
        finding_id = uuid4()
        digest = compute_traversed_state_digest(
            resolution_record_id=None,
            resolution_outcome=outcome.value,
            traversed_relationships=(),
            applied_policies=(),
        )
        evaluation_id = derive_ontology_impact_evaluation_id(
            tenant_id=TENANT,
            finding_family=FindingFamily.OQI1,
            finding_id=finding_id,
            finding_state_revision=1,
            traversed_state_digest=digest,
        )
        return OntologyImpactEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=TENANT,
            finding_family=FindingFamily.OQI1,
            finding_id=finding_id,
            finding_state_revision=1,
            outcome=outcome,
            resolution_record_id=None,
            traversed_state_digest=digest,
            evaluated_at=datetime.now(UTC),
            observations=observations,
            paths=(),
        )

    def test_impacted_requires_at_least_one_observation(self) -> None:
        with pytest.raises(ValidationException):
            self._build(outcome=ImpactOutcome.IMPACTED, observations=())

    def test_no_impact_must_have_zero_observations(self) -> None:
        with pytest.raises(ValidationException):
            self._build(
                outcome=ImpactOutcome.NO_IMPACT, observations=(_direct_observation(uuid4()),)
            )

    def test_impact_unknown_must_have_zero_observations(self) -> None:
        with pytest.raises(ValidationException):
            self._build(
                outcome=ImpactOutcome.IMPACT_UNKNOWN,
                observations=(_direct_observation(uuid4()),),
            )

    def test_valid_impacted_evaluation(self) -> None:
        evaluation = self._build(
            outcome=ImpactOutcome.IMPACTED, observations=(_direct_observation(uuid4()),)
        )
        assert evaluation.outcome is ImpactOutcome.IMPACTED

    def test_identity_tamper_detected(self) -> None:
        evaluation = self._build(
            outcome=ImpactOutcome.IMPACTED, observations=(_direct_observation(uuid4()),)
        )
        from dataclasses import replace

        with pytest.raises(ValidationException):
            replace(evaluation, evaluation_id=uuid4())

    def test_path_must_belong_to_a_propagated_observation(self) -> None:
        entity_id = uuid4()
        with pytest.raises(ValidationException):
            finding_id = uuid4()
            digest = compute_traversed_state_digest(
                resolution_record_id=None,
                resolution_outcome="IMPACTED",
                traversed_relationships=(),
                applied_policies=(),
            )
            OntologyImpactEvaluation(
                evaluation_id=derive_ontology_impact_evaluation_id(
                    tenant_id=TENANT,
                    finding_family=FindingFamily.OQI1,
                    finding_id=finding_id,
                    finding_state_revision=1,
                    traversed_state_digest=digest,
                ),
                tenant_id=TENANT,
                finding_family=FindingFamily.OQI1,
                finding_id=finding_id,
                finding_state_revision=1,
                outcome=ImpactOutcome.IMPACTED,
                resolution_record_id=None,
                traversed_state_digest=digest,
                evaluated_at=datetime.now(UTC),
                observations=(_direct_observation(uuid4()),),
                paths=(
                    OntologyImpactPath(
                        ontology_element_id=entity_id,
                        path_ordinal=0,
                        institutional_relationship_id=uuid4(),
                        direction="FORWARD",
                        policy_id=uuid4(),
                        policy_version_number=1,
                    ),
                ),
            )


class TestObservationShapeFirewall:
    def test_direct_must_have_depth_zero(self) -> None:
        with pytest.raises(ValidationException):
            OntologyImpactObservation(
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=uuid4(),
                impact_kind=ImpactClass.DIRECT,
                basis=ImpactBasis.DIRECT_ENTITY_IDENTITY_LINEAGE,
                depth=1,
            )

    def test_propagated_must_have_positive_depth(self) -> None:
        with pytest.raises(ValidationException):
            OntologyImpactObservation(
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=uuid4(),
                impact_kind=ImpactClass.PROPAGATED,
                basis=ImpactBasis.GOVERNED_RELATIONSHIP_PROPAGATION,
                depth=0,
            )

    def test_propagated_must_use_propagation_basis(self) -> None:
        with pytest.raises(ValidationException):
            OntologyImpactObservation(
                ontology_element_type=OntologyElementType.ENTITY,
                ontology_element_id=uuid4(),
                impact_kind=ImpactClass.PROPAGATED,
                basis=ImpactBasis.DIRECT_ENTITY_IDENTITY_LINEAGE,
                depth=1,
            )


class TestCurrentOntologyImpactIdentity:
    def test_condition_level_identity_excludes_evaluation(self) -> None:
        finding_id = uuid4()
        entity_id = uuid4()
        id_1 = derive_current_ontology_impact_id(
            tenant_id=TENANT,
            finding_family=FindingFamily.OQI1,
            finding_id=finding_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            impact_kind=ImpactClass.DIRECT,
        )
        id_2 = derive_current_ontology_impact_id(
            tenant_id=TENANT,
            finding_family=FindingFamily.OQI1,
            finding_id=finding_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            impact_kind=ImpactClass.DIRECT,
        )
        assert id_1 == id_2

    def test_valid_current_impact(self) -> None:
        finding_id = uuid4()
        entity_id = uuid4()
        current_impact_id = derive_current_ontology_impact_id(
            tenant_id=TENANT,
            finding_family=FindingFamily.OQI1,
            finding_id=finding_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            impact_kind=ImpactClass.DIRECT,
        )
        now = datetime.now(UTC)
        current = CurrentOntologyImpact(
            current_impact_id=current_impact_id,
            tenant_id=TENANT,
            finding_family=FindingFamily.OQI1,
            finding_id=finding_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            impact_kind=ImpactClass.DIRECT,
            status=CurrentImpactStatus.ACTIVE,
            latest_evaluation_id=uuid4(),
            first_seen_at=now,
            last_seen_at=now,
        )
        assert current.status is CurrentImpactStatus.ACTIVE
