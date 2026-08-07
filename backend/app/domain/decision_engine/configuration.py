from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True, slots=True)
class PolicyConfiguration:
    reference: str
    version: str


@dataclass(frozen=True, slots=True)
class DecisionConfidenceConfiguration:
    high_threshold: float
    medium_threshold: float


@dataclass(frozen=True, slots=True)
class DecisionConfigurationSchema:
    policy: PolicyConfiguration
    confidence: DecisionConfidenceConfiguration


class DecisionConfigurationValidator:
    def validate(self, configuration: DecisionConfigurationSchema) -> None:
        if not configuration.policy.reference.strip() or not configuration.policy.version.strip():
            raise ValueError("Decision policy reference and version are required")
        high = configuration.confidence.high_threshold
        medium = configuration.confidence.medium_threshold
        if not 0 <= medium <= high <= 1:
            raise ValueError("Decision confidence thresholds must satisfy 0 <= medium <= high <= 1")


class DecisionConfigurationLoader:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load(self) -> DecisionConfigurationSchema:
        configuration = DecisionConfigurationSchema(
            policy=PolicyConfiguration(
                reference=self.settings.decision_policy_reference,
                version=self.settings.decision_policy_version,
            ),
            confidence=DecisionConfidenceConfiguration(
                high_threshold=self.settings.decision_high_confidence_threshold,
                medium_threshold=self.settings.decision_medium_confidence_threshold,
            ),
        )
        DecisionConfigurationValidator().validate(configuration)
        return configuration
