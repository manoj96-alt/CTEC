"""OQI-H2 governed Reference Evidence (CDD-048 §15): a tenant-owned,
versioned assertion that a specific value is, independent of source
agreement or source authority, the correct value for a specific real-world
fact on a specific governed subject. Exactly three closed forms
(`GOVERNED_REFERENCE_DATASET`, `HUMAN_VERIFIED_EVIDENCE`,
`BUSINESS_RULE_DERIVED_VALUE`) -- no fourth form without a future
governance amendment.

`ReferenceEvidenceAssertion` is the shared envelope, following
`QualityCoveragePolicy`'s own precedent (CDD-047 §8-§11): `assertion_id` is
a caller-supplied, non-deterministic identity per version -- a governed
configuration/attestation act, not a machine-computed replay-safe evaluation
output -- versioned via `version_number`/`previous_version_id`, with at most
one `ACTIVE` version per `(tenant_id, ontology_element_type,
ontology_element_id, source_field_id, form)` enforced at the database level
(CDD-048 §15). Multiple forms may each hold their own `ACTIVE` assertion for
the same subject simultaneously -- this is what makes reference-evidence
conflict detection (CDD-048 §16) meaningful, never an error by itself.

Each form's specific provenance lives on its own normalized child value
object (`GovernedReferenceDatasetEntry`/`HumanVerifiedEvidenceEntry`/
`BusinessRuleDerivedReferenceEntry`), 1:1 with the envelope -- never a
generic JSON payload (CDD-048 §11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200
_MAX_CREATED_BY_LENGTH = 200
_MAX_VALUE_LENGTH = 4000
_MAX_DATASET_NAME_LENGTH = 200
_MAX_DATASET_VERSION_LENGTH = 64
_MAX_ENTRY_KEY_LENGTH = 1000
_MAX_ACTOR_ID_LENGTH = 200
_MAX_RATIONALE_LENGTH = 4000

#: CDD-048 §10.1, PO-02: H2 supports shared-platform governed reference
#: datasets only. Tenant-private reference datasets are explicitly deferred
#: -- this is a frozen constant, not a configurable field, so no code path
#: can silently introduce a tenant-owned dataset.
GOVERNED_REFERENCE_DATASET_OWNER = "SHARED_PLATFORM"


class ReferenceEvidenceForm(StrEnum):
    """CDD-048 §10, §15: closed, exactly these three. No fourth form."""

    GOVERNED_REFERENCE_DATASET = "GOVERNED_REFERENCE_DATASET"
    HUMAN_VERIFIED_EVIDENCE = "HUMAN_VERIFIED_EVIDENCE"
    BUSINESS_RULE_DERIVED_VALUE = "BUSINESS_RULE_DERIVED_VALUE"


class ReferenceEvidenceStatus(StrEnum):
    """CDD-048 §15, §27: closed, exactly these two. No DRAFT."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


@dataclass(frozen=True, slots=True)
class ReferenceEvidenceAssertion:
    """CDD-048 §15: the shared envelope. `asserted_value` is the claimed
    correct value, denormalized here for uniform read access regardless of
    form."""

    assertion_id: UUID
    tenant_id: str
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    source_field_id: UUID
    form: ReferenceEvidenceForm
    asserted_value: str
    status: ReferenceEvidenceStatus
    version_number: int
    previous_version_id: UUID | None
    created_by: str
    created_on: datetime
    retired_on: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.assertion_id, UUID):
            raise ValidationException("assertion_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException(
                f"tenant_id must be non-empty text of length <= {_MAX_TENANT_ID_LENGTH}"
            )
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.source_field_id, UUID):
            raise ValidationException("source_field_id must be a UUID")
        if not isinstance(self.form, ReferenceEvidenceForm):
            raise ValidationException("form must be a ReferenceEvidenceForm")
        if not isinstance(self.asserted_value, str) or not (
            1 <= len(self.asserted_value) <= _MAX_VALUE_LENGTH
        ):
            raise ValidationException("asserted_value must be non-empty bounded text")
        if not isinstance(self.status, ReferenceEvidenceStatus):
            raise ValidationException("status must be a ReferenceEvidenceStatus")
        if (
            not isinstance(self.version_number, int)
            or isinstance(self.version_number, bool)
            or self.version_number < 1
        ):
            raise ValidationException("version_number must be a positive integer")
        if self.previous_version_id is not None and not isinstance(self.previous_version_id, UUID):
            raise ValidationException("previous_version_id must be a UUID or None")
        if self.version_number == 1 and self.previous_version_id is not None:
            raise ValidationException("version_number=1 must not carry previous_version_id")
        if self.version_number > 1 and self.previous_version_id is None:
            raise ValidationException("version_number > 1 requires previous_version_id")
        if not isinstance(self.created_by, str) or not (
            1 <= len(self.created_by) <= _MAX_CREATED_BY_LENGTH
        ):
            raise ValidationException("created_by must be non-empty bounded text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")
        if self.status is ReferenceEvidenceStatus.ACTIVE and self.retired_on is not None:
            raise ValidationException("ACTIVE assertions must not carry retired_on")
        if self.status is ReferenceEvidenceStatus.RETIRED and self.retired_on is None:
            raise ValidationException("RETIRED assertions must carry retired_on")
        if self.retired_on is not None and self.retired_on.tzinfo is None:
            raise ValidationException("retired_on must include a timezone")


@dataclass(frozen=True, slots=True)
class GovernedReferenceDatasetEntry:
    """CDD-048 §10.1, §15: form-specific child for `GOVERNED_REFERENCE_
    DATASET`, 1:1 with its owning `ReferenceEvidenceAssertion`. The dataset
    itself is shared-platform (PO-02) -- this row records which governed,
    versioned dataset and lookup key back the tenant's assertion."""

    assertion_id: UUID
    dataset_name: str
    dataset_version: str
    entry_key: str

    def __post_init__(self) -> None:
        if not isinstance(self.assertion_id, UUID):
            raise ValidationException("assertion_id must be a UUID")
        if not isinstance(self.dataset_name, str) or not (
            1 <= len(self.dataset_name) <= _MAX_DATASET_NAME_LENGTH
        ):
            raise ValidationException("dataset_name must be non-empty bounded text")
        if not isinstance(self.dataset_version, str) or not (
            1 <= len(self.dataset_version) <= _MAX_DATASET_VERSION_LENGTH
        ):
            raise ValidationException("dataset_version must be non-empty bounded text")
        if not isinstance(self.entry_key, str) or not (
            1 <= len(self.entry_key) <= _MAX_ENTRY_KEY_LENGTH
        ):
            raise ValidationException("entry_key must be non-empty bounded text")


@dataclass(frozen=True, slots=True)
class HumanVerifiedEvidenceEntry:
    """CDD-048 §10.2, §17: form-specific child for `HUMAN_VERIFIED_
    EVIDENCE`. `verifying_actor_id` must be a real, non-anonymous human
    principal -- never an agent, never the rule-authoring principal (PO-03,
    enforced at the service/authorization layer, never here). `revoked_at`
    supersedes without rewriting history (CDD-048 §27) -- a revoked entry's
    owning assertion transitions to RETIRED via a new version, this field
    itself is never mutated once set."""

    assertion_id: UUID
    verifying_actor_id: str
    verification_timestamp: datetime
    verification_rationale: str
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.assertion_id, UUID):
            raise ValidationException("assertion_id must be a UUID")
        if not isinstance(self.verifying_actor_id, str) or not (
            1 <= len(self.verifying_actor_id) <= _MAX_ACTOR_ID_LENGTH
        ):
            raise ValidationException("verifying_actor_id must be non-empty bounded text")
        if self.verification_timestamp is None or self.verification_timestamp.tzinfo is None:
            raise ValidationException("verification_timestamp must include a timezone")
        if not isinstance(self.verification_rationale, str) or not (
            1 <= len(self.verification_rationale) <= _MAX_RATIONALE_LENGTH
        ):
            raise ValidationException("verification_rationale must be non-empty bounded text")
        if self.revoked_at is not None and self.revoked_at.tzinfo is None:
            raise ValidationException("revoked_at must include a timezone")


@dataclass(frozen=True, slots=True)
class BusinessRuleDerivedReferenceEntry:
    """CDD-048 §10.3, §18: form-specific child for `BUSINESS_RULE_DERIVED_
    VALUE`. Pins the exact deriving rule, version, and evaluation -- no
    probabilistic or LLM-produced value may ever back this form; enforced
    structurally by `deriving_evaluation_id` always referencing a real,
    immutable `BusinessRuleEvaluation` row produced only by OQI3's
    deterministic evaluator (CDD-048 §18)."""

    assertion_id: UUID
    deriving_business_rule_id: UUID
    deriving_rule_version: int
    deriving_evaluation_id: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.assertion_id, UUID):
            raise ValidationException("assertion_id must be a UUID")
        if not isinstance(self.deriving_business_rule_id, UUID):
            raise ValidationException("deriving_business_rule_id must be a UUID")
        if (
            not isinstance(self.deriving_rule_version, int)
            or isinstance(self.deriving_rule_version, bool)
            or self.deriving_rule_version < 1
        ):
            raise ValidationException("deriving_rule_version must be a positive integer")
        if not isinstance(self.deriving_evaluation_id, UUID):
            raise ValidationException("deriving_evaluation_id must be a UUID")


def activate_new_assertion_version(
    *,
    existing_active: ReferenceEvidenceAssertion | None,
    assertion_id: UUID,
    tenant_id: str,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    source_field_id: UUID,
    form: ReferenceEvidenceForm,
    asserted_value: str,
    created_by: str,
    created_on: datetime,
) -> ReferenceEvidenceAssertion:
    """CDD-048 §15, §27: constructs the next ACTIVE version for a
    `(tenant, subject, form)`. Retirement of `existing_active` (if any) is
    the caller's/repository's responsibility, mirroring `QualityRule`'s own
    `activate_new_version` precedent -- this function only ever returns the
    new version, never mutates `existing_active` in place (it is a frozen
    dataclass)."""
    return ReferenceEvidenceAssertion(
        assertion_id=assertion_id,
        tenant_id=tenant_id,
        ontology_element_type=ontology_element_type,
        ontology_element_id=ontology_element_id,
        source_field_id=source_field_id,
        form=form,
        asserted_value=asserted_value,
        status=ReferenceEvidenceStatus.ACTIVE,
        version_number=1 if existing_active is None else existing_active.version_number + 1,
        previous_version_id=None if existing_active is None else existing_active.assertion_id,
        created_by=created_by,
        created_on=created_on,
    )
