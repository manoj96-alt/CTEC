from enum import StrEnum


class LifecycleState(StrEnum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    ARCHIVED = "Archived"


class GovernanceStatus(StrEnum):
    PROPOSED = "Proposed"
    APPROVED = "Approved"
    RETIRED = "Retired"
    ARCHIVED = "Archived"
