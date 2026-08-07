# Generated repository registry.
from app.infrastructure.persistence.models import *
from app.infrastructure.persistence.repositories.accountable_owner_repository import (
    AccountableOwnerRepository,
)
from app.infrastructure.persistence.repositories.assertion_evidence_repository import (
    AssertionEvidenceRepository,
)
from app.infrastructure.persistence.repositories.assertion_repository import (
    AssertionRepository,
)
from app.infrastructure.persistence.repositories.business_domain_repository import (
    BusinessDomainRepository,
)
from app.infrastructure.persistence.repositories.context_repository import (
    ContextRepository,
)
from app.infrastructure.persistence.repositories.country_repository import (
    CountryRepository,
)
from app.infrastructure.persistence.repositories.decision_objective_repository import (
    DecisionObjectiveRepository,
)
from app.infrastructure.persistence.repositories.decision_repository import (
    DecisionRepository,
)
from app.infrastructure.persistence.repositories.decision_state_repository import (
    DecisionStateRepository,
)
from app.infrastructure.persistence.repositories.enterprise_entity_repository import (
    EnterpriseEntityRepository,
)
from app.infrastructure.persistence.repositories.enterprise_repository import (
    EnterpriseRepository,
)
from app.infrastructure.persistence.repositories.enterprise_type_repository import (
    EnterpriseTypeRepository,
)
from app.infrastructure.persistence.repositories.entity_type_repository import (
    EntityTypeRepository,
)
from app.infrastructure.persistence.repositories.evidence_repository import (
    EvidenceRepository,
)
from app.infrastructure.persistence.repositories.experience_repository import (
    ExperienceRepository,
)
from app.infrastructure.persistence.repositories.governance_repository import (
    GovernanceRepository,
)
from app.infrastructure.persistence.repositories.institutional_act_repository import (
    InstitutionalActRepository,
)
from app.infrastructure.persistence.repositories.institutional_action_repository import (
    InstitutionalActionRepository,
)
from app.infrastructure.persistence.repositories.institutional_concept_repository import (
    InstitutionalConceptRepository,
)
from app.infrastructure.persistence.repositories.institutional_relationship_assertion_repository import (
    InstitutionalRelationshipAssertionsRepository,
)
from app.infrastructure.persistence.repositories.institutional_relationship_repository import (
    InstitutionalRelationshipRepository,
)
from app.infrastructure.persistence.repositories.knowledge_repository import (
    KnowledgeRepository,
)
from app.infrastructure.persistence.repositories.occasion_repository import (
    OccasionRepository,
)
from app.infrastructure.persistence.repositories.outcome_repository import (
    OutcomeRepository,
)
from app.infrastructure.persistence.repositories.pattern_of_relevance_repository import (
    PatternOfRelevanceRepository,
)
from app.infrastructure.persistence.repositories.reason_decision_objective_repository import (
    ReasonDecisionObjectivesRepository,
)
from app.infrastructure.persistence.repositories.reason_evidence_repository import (
    ReasonEvidenceRepository,
)
from app.infrastructure.persistence.repositories.reason_graph_repository import (
    ReasonGraphRepository,
)
from app.infrastructure.persistence.repositories.reason_repository import (
    ReasonRepository,
)
from app.infrastructure.persistence.repositories.relationship_type_repository import (
    RelationshipTypeRepository,
)
from app.infrastructure.persistence.repositories.source_object_repository import (
    SourceObjectRepository,
)
from app.infrastructure.persistence.repositories.source_system_repository import (
    SourceSystemRepository,
)

REPOSITORY_TYPES = {
    Enterprise: EnterpriseRepository,
    EnterpriseType: EnterpriseTypeRepository,
    Country: CountryRepository,
    BusinessDomain: BusinessDomainRepository,
    InstitutionalConcept: InstitutionalConceptRepository,
    RelationshipType: RelationshipTypeRepository,
    EntityType: EntityTypeRepository,
    EnterpriseEntity: EnterpriseEntityRepository,
    Evidence: EvidenceRepository,
    Assertion: AssertionRepository,
    InstitutionalRelationship: InstitutionalRelationshipRepository,
    Knowledge: KnowledgeRepository,
    Reason: ReasonRepository,
    ReasonGraph: ReasonGraphRepository,
    DecisionObjective: DecisionObjectiveRepository,
    Occasion: OccasionRepository,
    PatternOfRelevance: PatternOfRelevanceRepository,
    Decision: DecisionRepository,
    DecisionState: DecisionStateRepository,
    InstitutionalAction: InstitutionalActionRepository,
    Outcome: OutcomeRepository,
    Experience: ExperienceRepository,
    Governance: GovernanceRepository,
    AccountableOwner: AccountableOwnerRepository,
    SourceSystem: SourceSystemRepository,
    SourceObject: SourceObjectRepository,
    InstitutionalAct: InstitutionalActRepository,
    Context: ContextRepository,
    ReasonDecisionObjectives: ReasonDecisionObjectivesRepository,
    ReasonEvidence: ReasonEvidenceRepository,
    AssertionEvidence: AssertionEvidenceRepository,
    InstitutionalRelationshipAssertions: InstitutionalRelationshipAssertionsRepository,
}
