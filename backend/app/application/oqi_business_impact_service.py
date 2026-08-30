"""CDD-044: OQI6 orchestration -- governed `BusinessProcess`/
`BusinessDependency` authoring, deterministic per-dependency Business
Impact derivation, and deterministic per-subject Reliance derivation. No
model provider dependency anywhere in this file (CDD-044 §34); no source
write; no direct mutation of any OQI1-5 Finding/impact/candidate/
authorization state (CDD-044 §33, §49-§50)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.domain.oqi_business_impact.dependency import (
    BusinessDependency,
    BusinessDependencyStatus,
    Criticality,
    create_business_dependency,
    new_business_dependency_version,
)
from app.domain.oqi_business_impact.impact import (
    BusinessImpactEvaluation,
    CurrentBusinessImpact,
    derive_business_impact_evaluation_id,
    derive_business_impact_outcome,
)
from app.domain.oqi_business_impact.process import (
    BusinessImpactCategory,
    BusinessProcess,
    create_business_process,
    new_business_process_version,
)
from app.domain.oqi_business_impact.reliance import (
    CurrentReliance,
    ReasonCode,
    RelianceEvaluation,
    compute_reliance_contributing_state_digest,
    derive_reliance_evaluation_id,
    derive_reliance_state,
)
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.oqi_business_impact import (
    CurrentBusinessImpactORM,
    CurrentRelianceORM,
)
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)


class OqiBusinessImpactService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._repository = OqiBusinessImpactRepositoryImpl(session)

    # ------------------------------------------------------------------
    # Governed authoring (CDD-044 §15-§16, §21-§23, §43-§44).
    # ------------------------------------------------------------------

    def create_process(
        self,
        *,
        tenant_id: str,
        name: str,
        description: str | None = None,
        category: BusinessImpactCategory | None = None,
        created_by: str,
        created_on: datetime,
    ) -> BusinessProcess:
        process = create_business_process(
            process_id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            description=description,
            category=category,
            created_by=created_by,
            created_on=created_on,
        )
        self._repository.insert_business_process(process)
        self.session.flush()
        return process

    def retire_process(
        self, *, tenant_id: str, process_id: UUID, created_by: str, created_on: datetime
    ) -> BusinessProcess:
        from app.domain.oqi_business_impact.process import BusinessProcessStatus

        prior = self._repository.get_latest_business_process(
            tenant_id=tenant_id, process_id=process_id
        )
        if prior is None:
            raise ValidationException(f"no BusinessProcess {process_id} for tenant {tenant_id!r}")
        new_version = new_business_process_version(
            prior,
            status=BusinessProcessStatus.RETIRED,
            created_by=created_by,
            created_on=created_on,
        )
        self._repository.insert_business_process(new_version)
        self.session.flush()
        return new_version

    def create_dependency(
        self,
        *,
        tenant_id: str,
        business_process_id: UUID,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        criticality: Criticality | None,
        created_by: str,
        created_on: datetime,
    ) -> BusinessDependency:
        process = self._repository.get_latest_business_process(
            tenant_id=tenant_id, process_id=business_process_id
        )
        if process is None:
            raise ValidationException(
                f"no BusinessProcess {business_process_id} for tenant {tenant_id!r}"
            )
        dependency = create_business_dependency(
            dependency_id=uuid4(),
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            business_process_version=process.version,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            criticality=criticality,
            created_by=created_by,
            created_on=created_on,
        )
        self._repository.insert_business_dependency(dependency)
        self.session.flush()
        return dependency

    def change_dependency_criticality(
        self,
        *,
        tenant_id: str,
        dependency_id: UUID,
        criticality: Criticality | None,
        created_by: str,
        created_on: datetime,
    ) -> BusinessDependency:
        """CDD-044 §22-§23: a criticality change is a new governed version
        -- the prior version row is never mutated, and every
        `BusinessImpactEvaluation` that already referenced it retains its
        own (dependency_id, version) binding untouched."""
        prior = self._repository.get_latest_business_dependency(
            tenant_id=tenant_id, dependency_id=dependency_id
        )
        if prior is None:
            raise ValidationException(
                f"no BusinessDependency {dependency_id} for tenant {tenant_id!r}"
            )
        new_version = new_business_dependency_version(
            prior, criticality=criticality, created_by=created_by, created_on=created_on
        )
        self._repository.insert_business_dependency(new_version)
        self.session.flush()
        return new_version

    def retire_dependency(
        self, *, tenant_id: str, dependency_id: UUID, created_by: str, created_on: datetime
    ) -> BusinessDependency:
        prior = self._repository.get_latest_business_dependency(
            tenant_id=tenant_id, dependency_id=dependency_id
        )
        if prior is None:
            raise ValidationException(
                f"no BusinessDependency {dependency_id} for tenant {tenant_id!r}"
            )
        new_version = new_business_dependency_version(
            prior,
            status=BusinessDependencyStatus.RETIRED,
            created_by=created_by,
            created_on=created_on,
        )
        self._repository.insert_business_dependency(new_version)
        self.session.flush()
        return new_version

    # ------------------------------------------------------------------
    # Deterministic Business Impact derivation (CDD-044 §20-§26, §59).
    # ------------------------------------------------------------------

    def evaluate_business_impact_for_dependency(
        self, *, tenant_id: str, dependency_id: UUID, evaluated_at: datetime
    ) -> BusinessImpactEvaluation:
        """CDD-044 §41: acquires OQI6's own dedicated advisory-lock
        namespace before reading+writing the mutable current projection,
        serializing concurrent re-evaluations of the same dependency."""
        dependency = self._repository.get_latest_business_dependency(
            tenant_id=tenant_id, dependency_id=dependency_id
        )
        if dependency is None:
            raise ValidationException(
                f"no BusinessDependency {dependency_id} for tenant {tenant_id!r}"
            )

        self._repository.acquire_current_projection_authority(f"business-impact:{dependency_id}")

        active_dependency_exists = dependency.status is BusinessDependencyStatus.ACTIVE
        impact_status = (
            self._repository.get_current_impact_status_for_subject(
                tenant_id=tenant_id,
                ontology_element_type=dependency.ontology_element_type,
                ontology_element_id=dependency.ontology_element_id,
            )
            if active_dependency_exists
            else None
        )
        outcome = derive_business_impact_outcome(
            active_dependency_exists=active_dependency_exists, impact_status=impact_status
        )

        # Re-derive the exact considered CurrentOntologyImpact identity (if any) for
        # deterministic evaluation identity -- reuse the same authorized read.
        considered_current_impact_id: UUID | None = None
        if impact_status is not None:
            impact_rows = OqiOntologyImpactEvaluationRepositoryImpl(
                self.session
            ).get_current_impacts_for_subject(
                tenant_id=tenant_id,
                ontology_element_type=dependency.ontology_element_type,
                ontology_element_id=dependency.ontology_element_id,
            )
            matching = [row for row in impact_rows if row.status is impact_status]
            if matching:
                considered_current_impact_id = min(
                    matching, key=lambda row: str(row.current_impact_id)
                ).current_impact_id

        evaluation_id = derive_business_impact_evaluation_id(
            tenant_id=tenant_id,
            business_dependency_id=dependency.dependency_id,
            business_dependency_version=dependency.version,
            considered_current_impact_id=considered_current_impact_id,
            outcome=outcome,
        )
        evaluation = BusinessImpactEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            business_dependency_id=dependency.dependency_id,
            business_dependency_version=dependency.version,
            ontology_element_type=dependency.ontology_element_type,
            ontology_element_id=dependency.ontology_element_id,
            outcome=outcome,
            considered_current_impact_id=considered_current_impact_id,
            evaluated_at=evaluated_at,
        )
        self._repository.insert_business_impact_evaluation_idempotent(evaluation)
        existing_current = self.session.get(
            CurrentBusinessImpactORM, (tenant_id, dependency.dependency_id)
        )
        first_seen_at = (
            existing_current.first_seen_at if existing_current is not None else evaluated_at
        )
        self._repository.upsert_current_business_impact(
            CurrentBusinessImpact(
                tenant_id=tenant_id,
                business_dependency_id=dependency.dependency_id,
                latest_evaluation_id=evaluation_id,
                first_seen_at=first_seen_at,
                last_seen_at=evaluated_at,
            )
        )
        self.session.flush()
        return evaluation

    # ------------------------------------------------------------------
    # Deterministic Reliance derivation (CDD-044 §8-§11, §18-§19, §58).
    # ------------------------------------------------------------------

    def evaluate_reliance_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        evaluated_at: datetime,
    ) -> RelianceEvaluation:
        self._repository.acquire_current_projection_authority(
            f"reliance:{ontology_element_type.value}:{ontology_element_id}"
        )

        subject_state = self._repository.compute_subject_finding_state(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
        )
        any_open = bool(subject_state.open_finding_refs)
        # See impact.py's own docstring: CurrentOntologyImpact never stores
        # IMPACT_UNKNOWN as a row of its own, so this branch of CDD-044
        # §58's decision table is not reachable via real persisted data --
        # kept as an explicit, always-False input rather than removed, so
        # the decision function's full documented contract stays intact.
        any_active_impact_unknown = False

        state, reason_codes = derive_reliance_state(
            any_open_finding=any_open,
            any_evaluation_ever_run=subject_state.any_evaluation_ever_run,
            any_active_impact_unknown=any_active_impact_unknown,
        )

        if any_open:
            pending = any(
                self._repository.has_pending_remediation_for_finding(
                    tenant_id=tenant_id, finding_family=family, finding_id=finding_id
                )
                for family, finding_id, _ in subject_state.open_finding_refs
            )
            if pending:
                reason_codes = (*reason_codes, ReasonCode.REMEDIATION_PENDING)

        digest = compute_reliance_contributing_state_digest(
            open_finding_refs=subject_state.open_finding_refs,
            any_evaluation_ever_run=subject_state.any_evaluation_ever_run,
            any_active_impact_unknown=any_active_impact_unknown,
        )
        evaluation_id = derive_reliance_evaluation_id(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            contributing_state_digest=digest,
        )
        evaluation = RelianceEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            state=state,
            reason_codes=reason_codes,
            contributing_state_digest=digest,
            evaluated_at=evaluated_at,
        )
        self._repository.insert_reliance_evaluation_idempotent(evaluation)

        existing_current = self.session.get(
            CurrentRelianceORM, (tenant_id, ontology_element_type.value, ontology_element_id)
        )
        first_seen_at = (
            existing_current.first_seen_at if existing_current is not None else evaluated_at
        )
        self._repository.upsert_current_reliance(
            CurrentReliance(
                tenant_id=tenant_id,
                ontology_element_type=ontology_element_type,
                ontology_element_id=ontology_element_id,
                latest_evaluation_id=evaluation_id,
                first_seen_at=first_seen_at,
                last_seen_at=evaluated_at,
            )
        )
        self.session.flush()
        return evaluation
