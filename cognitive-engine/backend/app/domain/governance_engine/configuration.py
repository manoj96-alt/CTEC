from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class PolicyConfiguration:
    reference: str
    version: str


@dataclass(frozen=True, slots=True)
class GovernanceConfidenceConfiguration:
    high_threshold: float
    medium_threshold: float


@dataclass(frozen=True, slots=True)
class GovernanceConfigurationSchema:
    policy: PolicyConfiguration
    confidence: GovernanceConfidenceConfiguration
    authorized_exception_authorities: tuple[str, ...]


class GovernanceConfigurationValidator:
    def validate(self, configuration: GovernanceConfigurationSchema) -> None:
        if not configuration.policy.reference.strip() or not configuration.policy.version.strip():
            raise ValueError("Governance policy reference and version are required")
        high = configuration.confidence.high_threshold
        medium = configuration.confidence.medium_threshold
        if not 0 <= medium <= high <= 1:
            raise ValueError(
                "Governance confidence thresholds must satisfy 0 <= medium <= high <= 1"
            )
        if any(
            not authority.strip() for authority in configuration.authorized_exception_authorities
        ):
            raise ValueError("Authorized exception authorities must be non-empty")


class GovernanceConfigurationLoader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load(self) -> GovernanceConfigurationSchema:
        configuration = GovernanceConfigurationSchema(
            policy=PolicyConfiguration(
                reference=self.settings.governance_policy_reference,
                version=self.settings.governance_policy_version,
            ),
            confidence=GovernanceConfidenceConfiguration(
                high_threshold=self.settings.governance_high_confidence_threshold,
                medium_threshold=self.settings.governance_medium_confidence_threshold,
            ),
            authorized_exception_authorities=tuple(
                self.settings.governance_authorized_exception_authorities
            ),
        )
        GovernanceConfigurationValidator().validate(configuration)
        return configuration
