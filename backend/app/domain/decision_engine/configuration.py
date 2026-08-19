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


# Gate F (CDD-015 §11, §23, §34; remediated per the merged Gate F Governed
# Impact Decision Policy Clarification and Remediation Report, PR #69): the
# governed four-condition binary policy's materiality threshold, verified
# directly against the frontend prototype source
# (`frontend/lib/demo/decision-rules.ts:11`): $10,000,000, applied to
# annual revenue exposure. Deliberately NOT sourced from `Settings`/the
# environment (no `core/config.py` change is authorized) -- a fixed,
# explicit, testable domain-layer policy constant is itself "a governed
# configuration value" (§34's own phrasing), distinct from CDD-011's
# existing, unmodified `DecisionConfigurationSchema`. No lead-time or
# candidate-cost threshold is authorized (merged clarification Amendments
# E/F) -- neither appears here.
GATE_F_MATERIALITY_THRESHOLD_USD = 10_000_000.0
GATE_F_POLICY_REFERENCE = "CDD-015-Gate-F-Mitigation-Policy"
GATE_F_POLICY_VERSION = "2.0"


@dataclass(frozen=True, slots=True)
class GateFPolicyConfiguration:
    policy_reference: str = GATE_F_POLICY_REFERENCE
    policy_version: str = GATE_F_POLICY_VERSION
    materiality_threshold_usd: float = GATE_F_MATERIALITY_THRESHOLD_USD


class GateFPolicyConfigurationValidator:
    def validate(self, configuration: GateFPolicyConfiguration) -> None:
        if not configuration.policy_reference.strip() or not configuration.policy_version.strip():
            raise ValueError("Gate F policy reference and version are required")
        if configuration.materiality_threshold_usd < 0:
            raise ValueError("Gate F materiality threshold must be non-negative")


def load_gate_f_policy_configuration() -> GateFPolicyConfiguration:
    configuration = GateFPolicyConfiguration()
    GateFPolicyConfigurationValidator().validate(configuration)
    return configuration
