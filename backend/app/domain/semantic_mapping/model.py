"""Domain model for a governed Source Field <-> Blueprint Information Element
correspondence (Gate H H1; CDD-019 §8, H1 Source Field / Semantic Mapping
Artifact Authorization). Expresses exactly one deterministic 1:1
correspondence between a `SourceField` and an
`InformationElementRequirement.information_element_requirement_id` --
referenced directly, with no intermediate `InformationElementDefinition`
(CDD-019 §10). Carries no computation, expression, transformation, or
condition field of any kind (CDD-019 §4, §12), and no `tenant_id` (tenant is
resolved transitively through `source_field_id`, CDD-019 §18)."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier


@dataclass(frozen=True, slots=True)
class SemanticMapping:
    semantic_mapping_id: Identifier
    source_field_id: Identifier
    information_element_requirement_id: Identifier
    lifecycle_state: LifecycleState
    governance_status: GovernanceStatus
    created_by: Identifier
    created_on: datetime
    modified_by: Identifier | None = None
    modified_on: datetime | None = None

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Semantic Mapping ID", self.semantic_mapping_id),
            ("Source Field", self.source_field_id),
            ("Information Element Requirement", self.information_element_requirement_id),
            ("Created By", self.created_by),
            ("Modified By", self.modified_by),
        ):
            if identifier_value is not None and not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if not isinstance(self.lifecycle_state, LifecycleState):
            raise ValidationException("Lifecycle State must be a Lifecycle State")
        if not isinstance(self.governance_status, GovernanceStatus):
            raise ValidationException("Governance Status must be a Governance Status")
        if self.created_on.tzinfo is None:
            raise ValidationException("Created On must include a timezone")
        if self.modified_on is not None and self.modified_on.tzinfo is None:
            raise ValidationException("Modified On must include a timezone")
