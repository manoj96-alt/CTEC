"""CDD-044: persistence and derivation orchestration for OQI6 --
Criticality, Business Impact & Explainable Reliance (Artifact Authorization
§2.1 row 7). Reads OQI1/OQI2/OQI3/OQI4's own governed persistence read-only
(via the four narrow additive methods authorized by CDD-044 §49/§49.1, plus
the pre-existing, unmodified `EntityResolutionStore` and Finding ORM
classes -- reading another domain's ORM class directly, without modifying
its owning file, is this repository's own established precedent, e.g.
`OqiOntologyImpactEvaluationRepositoryImpl.resolve_finding_subject` already
does exactly this for `QualityFindingORM`/`BusinessRuleFindingORM`/
`QualityComparisonFindingORM`). Never writes to any OQI1-5 table.

The "any OPEN Finding attributable to a subject" computation (CDD-044 §8.2,
§58) is folded into a single `UNION ALL` `Select` -- compiled and executed
by SQLAlchemy as one server-side statement, not sequential
independently-committed application reads -- covering both the direct path
(a Finding's own resolved evidence) and the indirect path (an `ACTIVE`
`CurrentOntologyImpact` row naming the subject), per CDD-044 §41's
temporal-coherence requirement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import literal, or_, select, text, union_all
from sqlalchemy.orm import Session

from app.domain.oqi_business_impact.dependency import BusinessDependency, BusinessDependencyStatus
from app.domain.oqi_business_impact.impact import BusinessImpactEvaluation, CurrentBusinessImpact
from app.domain.oqi_business_impact.process import BusinessProcess
from app.domain.oqi_business_impact.reliance import CurrentReliance, RelianceEvaluation
from app.domain.oqi_finding_origin.origin import FindingStorageFamily
from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    FindingFamily,
    OntologyElementType,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.oqi_business_impact import (
    CurrentBusinessImpactORM,
    CurrentRelianceORM,
    OqiBusinessDependencyORM,
    OqiBusinessImpactEvaluationORM,
    OqiBusinessProcessORM,
    OqiRelianceEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_cross_source_evaluation import (
    QualityComparisonEvaluationORM,
    QualityComparisonEvaluationParticipantORM,
)
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_integrity import (
    IntegrityReferenceFindingORM,
    IntegrityStructuralFindingORM,
)
from app.infrastructure.persistence.models.oqi_ontology_impact_evaluation import (
    CurrentOntologyImpactORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.models.oqi_timeliness import TimelinessFindingORM
from app.infrastructure.persistence.oqi_business_rule_evaluation_repository import (
    OqiBusinessRuleEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
    OqiCrossSourceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)

#: CDD-044 §41: distinct from every OQI1/2/3/4 seed already in use
#: (1, 2, 3 respectively; OQI4 introduces no new seed of its own).
OQI_BUSINESS_IMPACT_ADVISORY_LOCK_SEED = 4


@dataclass(frozen=True, slots=True)
class SubjectFindingState:
    """The exact governed facts CDD-044 needs about one ontology subject's
    own Finding/coverage state -- nothing more.

    CDD-050 §22: `open_finding_refs`'s first tuple element now legitimately
    carries either a `FindingFamily` (OQI1/OQI2/OQI3) or a
    `FindingStorageFamily.INTEGRITY` member -- both StrEnum, both safe for
    the `.value`/`str()` access every existing downstream consumer
    (`oqi_business_impact_service.py`, `domain/oqi_business_impact/
    reliance.py`) already performs, neither of which this phase authorizes
    touching. `Any` is a deliberate, narrow type-escape at exactly this one
    crossing point -- every value placed here really is a `.value`-bearing
    StrEnum member; nothing about runtime behavior changes."""

    open_finding_refs: tuple[tuple[Any, UUID, int], ...]
    any_evaluation_ever_run: bool


class OqiBusinessImpactRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Entity-resolution reverse lookup (read-only; zero new resolution
    # records; zero modification to entity_resolution_store.py).
    # ------------------------------------------------------------------

    def _resolve_source_object_ids_for_entity(
        self, *, tenant_id: str, entity_id: UUID
    ) -> tuple[UUID, ...]:
        store = EntityResolutionStore(self.session)
        ids: set[UUID] = set()
        for record in store.list_current_records(tenant_id):
            if record.enterprise_entity_id != entity_id:
                continue
            for raw in record.supporting_source_object_ids:
                ids.add(raw if isinstance(raw, UUID) else UUID(str(raw)))
        return tuple(ids)

    # ------------------------------------------------------------------
    # Subject Finding/coverage state (CDD-044 §8, §18, §41).
    # ------------------------------------------------------------------

    def compute_subject_finding_state(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> SubjectFindingState:
        """CDD-044 §41: the open-Finding computation is one `UNION ALL`
        `Select`, executed as a single statement. No attribute/assertion-
        level Reliance subject exists (CDD-044 §19); a `RELATIONSHIP`
        subject has no direct source-evidence chain of its own, so only
        the indirect (impact-linked) path applies to it."""
        source_object_ids = (
            self._resolve_source_object_ids_for_entity(
                tenant_id=tenant_id, entity_id=ontology_element_id
            )
            if ontology_element_type is OntologyElementType.ENTITY
            else ()
        )

        selects = []
        if source_object_ids:
            selects.append(
                select(
                    literal(FindingFamily.OQI1.value).label("family"),
                    QualityFindingORM.finding_id,
                    QualityFindingORM.state_revision,
                ).where(
                    QualityFindingORM.tenant_id == tenant_id,
                    QualityFindingORM.status == "OPEN",
                    QualityFindingORM.source_object_id.in_(source_object_ids),
                )
            )
            # BusinessRuleFindingORM has no source_object_id column of its
            # own -- its subject is `subject_identity`, the length-prefixed
            # concatenation of (source_object_id, source_record_reference)
            # from `canonical_single_record_subject_identity`. Matching on
            # the source_object_id's own length-prefixed encoding as a
            # prefix is exact (self-delimiting -- no other string can
            # produce the identical prefix bytes for a different id).
            subject_identity_prefixes = tuple(
                f"{len(str(source_object_id).encode('utf-8'))}:{source_object_id}%"
                for source_object_id in source_object_ids
            )
            selects.append(
                select(
                    literal(FindingFamily.OQI3.value).label("family"),
                    BusinessRuleFindingORM.finding_id,
                    BusinessRuleFindingORM.state_revision,
                ).where(
                    BusinessRuleFindingORM.tenant_id == tenant_id,
                    BusinessRuleFindingORM.status == "OPEN",
                    or_(
                        *(
                            BusinessRuleFindingORM.subject_identity.like(prefix)
                            for prefix in subject_identity_prefixes
                        )
                    ),
                )
            )
            selects.append(
                select(
                    literal(FindingFamily.OQI2.value).label("family"),
                    QualityComparisonFindingORM.finding_id,
                    QualityComparisonFindingORM.state_revision,
                )
                .select_from(QualityComparisonFindingORM)
                .join(
                    QualityComparisonEvaluationORM,
                    (
                        QualityComparisonEvaluationORM.comparison_subject_id
                        == QualityComparisonFindingORM.comparison_subject_id
                    )
                    & (
                        QualityComparisonEvaluationORM.tenant_id
                        == QualityComparisonFindingORM.tenant_id
                    ),
                )
                .join(
                    QualityComparisonEvaluationParticipantORM,
                    QualityComparisonEvaluationParticipantORM.evaluation_id
                    == QualityComparisonEvaluationORM.evaluation_id,
                )
                .where(
                    QualityComparisonFindingORM.tenant_id == tenant_id,
                    QualityComparisonFindingORM.status == "OPEN",
                    QualityComparisonEvaluationParticipantORM.source_object_id.in_(
                        source_object_ids
                    ),
                )
                .distinct()
            )

        # Indirect path: an ACTIVE CurrentOntologyImpact row naming this
        # subject, joined back to its own OPEN Finding -- covers subjects
        # reached only via OQI4 propagation, and RELATIONSHIP subjects.
        selects.append(
            select(
                literal(FindingFamily.OQI1.value).label("family"),
                QualityFindingORM.finding_id,
                QualityFindingORM.state_revision,
            )
            .select_from(CurrentOntologyImpactORM)
            .join(
                QualityFindingORM,
                QualityFindingORM.finding_id == CurrentOntologyImpactORM.finding_id,
            )
            .where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
                CurrentOntologyImpactORM.status == CurrentImpactStatus.ACTIVE.value,
                CurrentOntologyImpactORM.finding_family == FindingFamily.OQI1.value,
                QualityFindingORM.status == "OPEN",
            )
        )
        selects.append(
            select(
                literal(FindingFamily.OQI2.value).label("family"),
                QualityComparisonFindingORM.finding_id,
                QualityComparisonFindingORM.state_revision,
            )
            .select_from(CurrentOntologyImpactORM)
            .join(
                QualityComparisonFindingORM,
                QualityComparisonFindingORM.finding_id == CurrentOntologyImpactORM.finding_id,
            )
            .where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
                CurrentOntologyImpactORM.status == CurrentImpactStatus.ACTIVE.value,
                CurrentOntologyImpactORM.finding_family == FindingFamily.OQI2.value,
                QualityComparisonFindingORM.status == "OPEN",
            )
        )
        selects.append(
            select(
                literal(FindingFamily.OQI3.value).label("family"),
                BusinessRuleFindingORM.finding_id,
                BusinessRuleFindingORM.state_revision,
            )
            .select_from(CurrentOntologyImpactORM)
            .join(
                BusinessRuleFindingORM,
                BusinessRuleFindingORM.finding_id == CurrentOntologyImpactORM.finding_id,
            )
            .where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
                CurrentOntologyImpactORM.status == CurrentImpactStatus.ACTIVE.value,
                CurrentOntologyImpactORM.finding_family == FindingFamily.OQI3.value,
                BusinessRuleFindingORM.status == "OPEN",
            )
        )
        # CDD-050 §22: exactly two new indirect-path branches -- Integrity
        # Findings reach a subject only via OQI4 propagation (Structural's
        # own subject is a direct EnterpriseEntity, never a source_object_id,
        # so it has no direct-path branch above; the same is true for
        # Reference unless/until its source resolves, per §20's own
        # resolver). Mirrors the three existing indirect-path branches'
        # exact shape.
        selects.append(
            select(
                literal(FindingStorageFamily.INTEGRITY.value).label("family"),
                IntegrityStructuralFindingORM.finding_id,
                IntegrityStructuralFindingORM.state_revision,
            )
            .select_from(CurrentOntologyImpactORM)
            .join(
                IntegrityStructuralFindingORM,
                IntegrityStructuralFindingORM.finding_id == CurrentOntologyImpactORM.finding_id,
            )
            .where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
                CurrentOntologyImpactORM.status == CurrentImpactStatus.ACTIVE.value,
                CurrentOntologyImpactORM.finding_family == FindingStorageFamily.INTEGRITY.value,
                IntegrityStructuralFindingORM.status == "OPEN",
            )
        )
        selects.append(
            select(
                literal(FindingStorageFamily.INTEGRITY.value).label("family"),
                IntegrityReferenceFindingORM.finding_id,
                IntegrityReferenceFindingORM.state_revision,
            )
            .select_from(CurrentOntologyImpactORM)
            .join(
                IntegrityReferenceFindingORM,
                IntegrityReferenceFindingORM.finding_id == CurrentOntologyImpactORM.finding_id,
            )
            .where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
                CurrentOntologyImpactORM.status == CurrentImpactStatus.ACTIVE.value,
                CurrentOntologyImpactORM.finding_family == FindingStorageFamily.INTEGRITY.value,
                IntegrityReferenceFindingORM.status == "OPEN",
            )
        )
        # CDD-051 §24: one new indirect-path branch -- a Timeliness
        # Finding's subject is a source_object_id, reaching an ontology
        # subject only via OQI4 propagation (identical shape to Reference
        # Integrity's own indirect-path branch above), never a direct
        # EnterpriseEntity subject.
        selects.append(
            select(
                literal(FindingStorageFamily.TIMELINESS.value).label("family"),
                TimelinessFindingORM.finding_id,
                TimelinessFindingORM.state_revision,
            )
            .select_from(CurrentOntologyImpactORM)
            .join(
                TimelinessFindingORM,
                TimelinessFindingORM.finding_id == CurrentOntologyImpactORM.finding_id,
            )
            .where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
                CurrentOntologyImpactORM.status == CurrentImpactStatus.ACTIVE.value,
                CurrentOntologyImpactORM.finding_family == FindingStorageFamily.TIMELINESS.value,
                TimelinessFindingORM.status == "OPEN",
            )
        )

        combined = union_all(*selects)
        rows = self.session.execute(combined).all()
        open_refs: set[tuple[Any, UUID, int]] = set()
        for family, finding_id, state_revision in rows:
            try:
                resolved_family: Any = FindingFamily(family)
            except ValueError:
                resolved_family = FindingStorageFamily(family)
            open_refs.add((resolved_family, finding_id, state_revision))

        # CDD-044 §41's own coverage formula, byte-for-byte unmodified --
        # this is the exact legacy value CDD-047 §16/§18 requires be passed
        # through, unaltered, to the no-policy branch below.
        legacy_any_evaluation_ever_run = bool(open_refs) or (
            self._compute_coverage(tenant_id=tenant_id, source_object_ids=source_object_ids)
            if ontology_element_type is OntologyElementType.ENTITY
            else False
        )

        # CDD-047 §13/§17, Artifact Authorization row 12: generalized
        # coverage. No ACTIVE QualityCoveragePolicy -> returns
        # `legacy_any_evaluation_ever_run` verbatim (CDD-047 §16's
        # backward-compatibility identity requirement). An ACTIVE policy
        # requires qualifying coverage for every one of its required
        # CoverageDimension members, independent of open-Finding state --
        # `derive_reliance_state`'s own first decision branch already
        # short-circuits to AT_RISK on any open Finding regardless of this
        # value, so no double-counting of open_refs is needed here.
        any_evaluation_ever_run = OqiQualityCoveragePolicyRepositoryImpl(
            self.session
        ).compute_generalized_coverage(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
            source_object_ids=source_object_ids,
            legacy_any_evaluation_ever_run=legacy_any_evaluation_ever_run,
        )

        return SubjectFindingState(
            open_finding_refs=tuple(sorted(open_refs, key=lambda r: (r[0].value, str(r[1])))),
            any_evaluation_ever_run=any_evaluation_ever_run,
        )

    def _compute_coverage(self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]) -> bool:
        """CDD-044 §18: coverage is a boolean existence predicate over real
        persisted evaluation rows of any OQI1/2/3 family, regardless of
        outcome -- using the three narrow additive methods CDD-044
        §49.1 authorizes."""
        if not source_object_ids:
            return False
        oqi1 = OqiQualityEvaluationRepositoryImpl(
            self.session
        ).has_any_evaluation_for_source_objects(
            tenant_id=tenant_id, source_object_ids=source_object_ids
        )
        if oqi1:
            return True
        oqi2 = OqiCrossSourceEvaluationRepositoryImpl(
            self.session
        ).has_any_evaluation_for_source_objects(
            tenant_id=tenant_id, source_object_ids=source_object_ids
        )
        if oqi2:
            return True
        return OqiBusinessRuleEvaluationRepositoryImpl(
            self.session
        ).has_any_evaluation_for_source_objects(
            tenant_id=tenant_id, source_object_ids=source_object_ids
        )

    def get_current_impact_status_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> CurrentImpactStatus | None:
        """CDD-044 §49's newly-authorized `get_current_impacts_for_subject`.
        Aggregates across every Finding that resolved to this subject:
        `ACTIVE` if any row is `ACTIVE` (a currently proven impact from any
        contributing Finding outranks a merely `RESOLVED` one), else
        `RESOLVED` if any row is `RESOLVED`, else `None` (no row exists --
        see `derive_business_impact_outcome`'s own docstring for why this
        must map to `BUSINESS_IMPACT_UNKNOWN`, never `NO_KNOWN_...`)."""
        rows = OqiOntologyImpactEvaluationRepositoryImpl(
            self.session
        ).get_current_impacts_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
        )
        if any(row.status is CurrentImpactStatus.ACTIVE for row in rows):
            return CurrentImpactStatus.ACTIVE
        if any(row.status is CurrentImpactStatus.RESOLVED for row in rows):
            return CurrentImpactStatus.RESOLVED
        return None

    # ------------------------------------------------------------------
    # Advisory lock (CDD-044 §41, dedicated seed).
    # ------------------------------------------------------------------

    def acquire_current_projection_authority(self, identity: str) -> None:
        """`pg_advisory_xact_lock` -- released automatically on COMMIT,
        ROLLBACK, or connection loss. Never `pg_advisory_lock`
        (session-scoped), mirroring OQI1/2/3's identical mechanism with a
        distinct seed."""
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_BUSINESS_IMPACT_ADVISORY_LOCK_SEED},
        )

    # ------------------------------------------------------------------
    # BusinessProcess.
    # ------------------------------------------------------------------

    def insert_business_process(self, process: BusinessProcess) -> None:
        self.session.add(
            OqiBusinessProcessORM(
                process_id=process.process_id,
                version=process.version,
                tenant_id=process.tenant_id,
                name=process.name,
                description=process.description,
                status=process.status.value,
                category=None if process.category is None else process.category.value,
                created_by=process.created_by,
                created_on=process.created_on,
            )
        )

    def get_latest_business_process(
        self, *, tenant_id: str, process_id: UUID
    ) -> BusinessProcess | None:
        from app.domain.oqi_business_impact.process import (
            BusinessImpactCategory,
            BusinessProcessStatus,
        )

        model = (
            self.session.query(OqiBusinessProcessORM)
            .filter(
                OqiBusinessProcessORM.tenant_id == tenant_id,
                OqiBusinessProcessORM.process_id == process_id,
            )
            .order_by(OqiBusinessProcessORM.version.desc())
            .first()
        )
        if model is None:
            return None
        return BusinessProcess(
            process_id=model.process_id,
            tenant_id=model.tenant_id,
            version=model.version,
            name=model.name,
            description=model.description,
            status=BusinessProcessStatus(model.status),
            category=None if model.category is None else BusinessImpactCategory(model.category),
            created_by=model.created_by,
            created_on=model.created_on,
        )

    # ------------------------------------------------------------------
    # BusinessDependency.
    # ------------------------------------------------------------------

    def insert_business_dependency(self, dependency: BusinessDependency) -> None:
        self.session.add(
            OqiBusinessDependencyORM(
                dependency_id=dependency.dependency_id,
                version=dependency.version,
                tenant_id=dependency.tenant_id,
                business_process_id=dependency.business_process_id,
                business_process_version=dependency.business_process_version,
                ontology_element_type=dependency.ontology_element_type.value,
                ontology_element_id=dependency.ontology_element_id,
                criticality=(
                    None if dependency.criticality is None else dependency.criticality.value
                ),
                status=dependency.status.value,
                created_by=dependency.created_by,
                created_on=dependency.created_on,
            )
        )

    def get_latest_business_dependency(
        self, *, tenant_id: str, dependency_id: UUID
    ) -> BusinessDependency | None:

        model = (
            self.session.query(OqiBusinessDependencyORM)
            .filter(
                OqiBusinessDependencyORM.tenant_id == tenant_id,
                OqiBusinessDependencyORM.dependency_id == dependency_id,
            )
            .order_by(OqiBusinessDependencyORM.version.desc())
            .first()
        )
        if model is None:
            return None
        return self._dependency_to_domain(model)

    def _dependency_to_domain(self, model: OqiBusinessDependencyORM) -> BusinessDependency:
        from app.domain.oqi_business_impact.dependency import Criticality

        return BusinessDependency(
            dependency_id=model.dependency_id,
            tenant_id=model.tenant_id,
            version=model.version,
            business_process_id=model.business_process_id,
            business_process_version=model.business_process_version,
            ontology_element_type=OntologyElementType(model.ontology_element_type),
            ontology_element_id=model.ontology_element_id,
            criticality=None if model.criticality is None else Criticality(model.criticality),
            status=BusinessDependencyStatus(model.status),
            created_by=model.created_by,
            created_on=model.created_on,
        )

    def list_active_dependencies_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> tuple[BusinessDependency, ...]:
        """Every dependency naming this subject, restricted to each
        `dependency_id`'s own latest version, restricted to `ACTIVE`
        (CDD-044 §31: computed per dependency, never collapsed to one)."""
        rows = (
            self.session.query(OqiBusinessDependencyORM)
            .filter(
                OqiBusinessDependencyORM.tenant_id == tenant_id,
                OqiBusinessDependencyORM.ontology_element_type == ontology_element_type.value,
                OqiBusinessDependencyORM.ontology_element_id == ontology_element_id,
            )
            .order_by(
                OqiBusinessDependencyORM.dependency_id, OqiBusinessDependencyORM.version.desc()
            )
            .all()
        )
        latest_by_id: dict[UUID, OqiBusinessDependencyORM] = {}
        for row in rows:
            if row.dependency_id not in latest_by_id:
                latest_by_id[row.dependency_id] = row
        return tuple(
            self._dependency_to_domain(model)
            for model in latest_by_id.values()
            if model.status == BusinessDependencyStatus.ACTIVE.value
        )

    # ------------------------------------------------------------------
    # BusinessImpactEvaluation / CurrentBusinessImpact.
    # ------------------------------------------------------------------

    def insert_business_impact_evaluation_idempotent(
        self, evaluation: BusinessImpactEvaluation
    ) -> bool:
        existing = self.session.get(OqiBusinessImpactEvaluationORM, evaluation.evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            OqiBusinessImpactEvaluationORM(
                evaluation_id=evaluation.evaluation_id,
                tenant_id=evaluation.tenant_id,
                business_dependency_id=evaluation.business_dependency_id,
                business_dependency_version=evaluation.business_dependency_version,
                ontology_element_type=evaluation.ontology_element_type.value,
                ontology_element_id=evaluation.ontology_element_id,
                outcome=evaluation.outcome.value,
                considered_current_impact_id=evaluation.considered_current_impact_id,
                evaluated_at=evaluation.evaluated_at,
            )
        )
        self.session.flush()
        return True

    def upsert_current_business_impact(self, current: CurrentBusinessImpact) -> None:
        model = self.session.get(
            CurrentBusinessImpactORM, (current.tenant_id, current.business_dependency_id)
        )
        if model is None:
            self.session.add(
                CurrentBusinessImpactORM(
                    tenant_id=current.tenant_id,
                    business_dependency_id=current.business_dependency_id,
                    latest_evaluation_id=current.latest_evaluation_id,
                    first_seen_at=current.first_seen_at,
                    last_seen_at=current.last_seen_at,
                )
            )
            return
        model.latest_evaluation_id = current.latest_evaluation_id
        model.last_seen_at = current.last_seen_at

    # ------------------------------------------------------------------
    # RelianceEvaluation / CurrentReliance.
    # ------------------------------------------------------------------

    def insert_reliance_evaluation_idempotent(self, evaluation: RelianceEvaluation) -> bool:
        existing = self.session.get(OqiRelianceEvaluationORM, evaluation.evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            OqiRelianceEvaluationORM(
                evaluation_id=evaluation.evaluation_id,
                tenant_id=evaluation.tenant_id,
                ontology_element_type=evaluation.ontology_element_type.value,
                ontology_element_id=evaluation.ontology_element_id,
                state=evaluation.state.value,
                reason_codes=[code.value for code in evaluation.reason_codes],
                contributing_state_digest=evaluation.contributing_state_digest,
                evaluated_at=evaluation.evaluated_at,
            )
        )
        self.session.flush()
        return True

    def upsert_current_reliance(self, current: CurrentReliance) -> None:
        model = self.session.get(
            CurrentRelianceORM,
            (current.tenant_id, current.ontology_element_type.value, current.ontology_element_id),
        )
        if model is None:
            self.session.add(
                CurrentRelianceORM(
                    tenant_id=current.tenant_id,
                    ontology_element_type=current.ontology_element_type.value,
                    ontology_element_id=current.ontology_element_id,
                    latest_evaluation_id=current.latest_evaluation_id,
                    first_seen_at=current.first_seen_at,
                    last_seen_at=current.last_seen_at,
                )
            )
            return
        model.latest_evaluation_id = current.latest_evaluation_id
        model.last_seen_at = current.last_seen_at

    # ------------------------------------------------------------------
    # OQI5 read-only, non-authoritative REMEDIATION_PENDING annotation
    # (CDD-044 §33, §36, §50). Reads `oqi_remediation_cases` directly --
    # a read, never a write, never an input to any state decision.
    # ------------------------------------------------------------------

    def has_pending_remediation_for_finding(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> bool:
        from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily
        from app.domain.oqi_remediation.case import derive_remediation_case_id
        from app.infrastructure.persistence.models.oqi_remediation import OqiRemediationCaseORM

        try:
            remediation_family = RemediationFindingFamily(finding_family.value)
        except ValueError:
            # CDD-050 §25: a FindingStorageFamily.INTEGRITY-origin Finding
            # (or any other family RemediationFindingFamily -- OQI1/2/3
            # only -- does not recognize) never creates an
            # OqiRemediationCaseORM row at all: zero candidates always
            # (mirrors REASONABLENESS's own precedent), so honestly, no
            # pending case can ever exist for it.
            return False
        case_id = derive_remediation_case_id(
            tenant_id=tenant_id,
            finding_family=remediation_family,
            finding_id=finding_id,
        )
        model = self.session.get(OqiRemediationCaseORM, case_id)
        return model is not None and model.tenant_id == tenant_id
