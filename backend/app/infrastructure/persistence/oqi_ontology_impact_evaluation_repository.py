"""CDD-042 §4.3, §9-§11, §14: the Finding-family adapter lookups (read-only
consumption of OQI1/OQI2/OQI3's own governed persistence, never a write),
direct-impact resolution via the existing `EntityResolutionStore` (OQI4
performs zero new probabilistic matching and creates zero resolution
records), the single recursive-CTE propagation statement (CDD-042 §9 --
release-critical: institutional relationships AND the ACTIVE propagation-
policy set are read inside the SAME PostgreSQL statement, never as two
separate statements under READ COMMITTED), and parent-gated idempotent
persistence of the immutable Evaluation/Observation/Path ledger plus the
current-impact projection (CDD-042 §14, reusing OQI3's proven
`INSERT ... ON CONFLICT DO NOTHING RETURNING` pattern -- no new advisory-
lock seed is introduced, CDD-042 §14)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    CurrentOntologyImpact,
    FindingFamily,
    ImpactBasis,
    ImpactClass,
    ImpactOutcome,
    OntologyElementType,
    OntologyImpactEvaluation,
    OntologyImpactObservation,
    OntologyImpactPath,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.oqi_business_rule_evaluation import (
    BusinessRuleEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_business_rule_finding import BusinessRuleFindingORM
from app.infrastructure.persistence.models.oqi_cross_source_finding import (
    QualityComparisonFindingORM,
)
from app.infrastructure.persistence.models.oqi_ontology_impact_evaluation import (
    CurrentOntologyImpactORM,
    OntologyImpactEvaluationORM,
    OntologyImpactObservationORM,
    OntologyImpactPathORM,
)
from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM
from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
    OqiCrossSourceCorrespondenceRepositoryImpl,
)

#: CDD-042 §9's secondary global safety ceiling. A single malformed/overly
#: broad policy's own `max_depth` can never make traversal unbounded even
#: if per-policy depth validation were ever bypassed.
GLOBAL_MAX_DEPTH_CEILING = 10

#: CDD-042 §9: at most this many distinct shortest paths are retained as
#: evidence per propagated element per evaluation -- bounded, not "every
#: path", not "first found".
MAX_RETAINED_PATHS_PER_ELEMENT = 3


class FindingNotFoundError(Exception):
    """No Finding exists for the given (tenant, finding_family, finding_id),
    or it belongs to a different tenant than the one requested -- the
    caller never learns which (fail-closed, mirroring
    `EntityResolutionStore`'s own tenant-lookup discipline)."""


@dataclass(frozen=True, slots=True)
class ResolvedFindingSubject:
    """The Finding-family adapter's normalized output (CDD-042 §10). Exactly
    one `source_object_id`/`source_record_reference` pair for OQI1/OQI3;
    one pair per governed participant for OQI2 (CDD-042 §4.6)."""

    finding_state_revision: int
    source_object_ids: tuple[UUID, ...]
    source_record_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DirectImpactResult:
    outcome: ImpactOutcome
    resolution_record_id: UUID | None
    entity_id: UUID | None


@dataclass(frozen=True, slots=True)
class PropagatedPathCandidate:
    entity_id: UUID
    depth: int
    relationship_ids: tuple[UUID, ...]
    policy_ids: tuple[UUID, ...]
    policy_versions: tuple[int, ...]
    directions: tuple[str, ...]


class OqiOntologyImpactEvaluationRepository(Protocol):
    def resolve_finding_subject(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> ResolvedFindingSubject: ...

    def resolve_direct_impact(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]
    ) -> DirectImpactResult: ...

    def traverse_propagation(
        self,
        *,
        tenant_id: str,
        direct_entity_id: UUID,
        _test_only_delay_seconds: float | None = None,
    ) -> tuple[PropagatedPathCandidate, ...]: ...

    def insert_evaluation_idempotent(self, evaluation: OntologyImpactEvaluation) -> bool: ...

    def upsert_current_impact(self, current_impact: CurrentOntologyImpact) -> None: ...

    def get_current_impacts_for_finding(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> tuple[CurrentOntologyImpact, ...]: ...

    # `get_current_impacts_for_subject` (CDD-044 §49) is intentionally NOT
    # declared on this Protocol -- OQI6 always consumes the concrete
    # `OqiOntologyImpactEvaluationRepositoryImpl` directly (never through
    # this Protocol type), so adding it here would force every existing
    # fake/test double already structurally typed against this Protocol
    # (e.g. `test_oqi_ontology_impact_service.py`'s `_FakeRepository`) to
    # implement a method they have no use for -- an unnecessary and
    # unauthorized ripple into a file outside CDD-044's exact 26-path
    # authorization. The method exists only on the concrete class below.


class OqiOntologyImpactEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Finding-family adapter (CDD-042 §10) -- read-only.
    # ------------------------------------------------------------------

    def resolve_finding_subject(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> ResolvedFindingSubject:
        if finding_family is FindingFamily.OQI1:
            model = self.session.get(QualityFindingORM, finding_id)
            if model is None or model.tenant_id != tenant_id:
                raise FindingNotFoundError(f"No OQI1 Finding {finding_id} for tenant {tenant_id!r}")
            return ResolvedFindingSubject(
                finding_state_revision=model.state_revision,
                source_object_ids=(model.source_object_id,),
                source_record_references=(model.source_record_reference,),
            )
        if finding_family is FindingFamily.OQI3:
            finding_model = self.session.get(BusinessRuleFindingORM, finding_id)
            if finding_model is None or finding_model.tenant_id != tenant_id:
                raise FindingNotFoundError(f"No OQI3 Finding {finding_id} for tenant {tenant_id!r}")
            evaluation_model = self.session.get(
                BusinessRuleEvaluationORM, finding_model.latest_evaluation_id
            )
            if evaluation_model is None or evaluation_model.tenant_id != tenant_id:
                raise FindingNotFoundError(
                    f"OQI3 Finding {finding_id}'s latest_evaluation_id is not tenant-consistent"
                )
            return ResolvedFindingSubject(
                finding_state_revision=finding_model.state_revision,
                source_object_ids=(evaluation_model.source_object_id,),
                source_record_references=(evaluation_model.source_record_reference,),
            )
        if finding_family is FindingFamily.OQI2:
            comparison_finding_model = self.session.get(QualityComparisonFindingORM, finding_id)
            if comparison_finding_model is None or comparison_finding_model.tenant_id != tenant_id:
                raise FindingNotFoundError(f"No OQI2 Finding {finding_id} for tenant {tenant_id!r}")
            correspondence = OqiCrossSourceCorrespondenceRepositoryImpl(self.session).get_active(
                tenant_id=tenant_id,
                comparison_subject_id=comparison_finding_model.comparison_subject_id,
            )
            if correspondence is None:
                raise FindingNotFoundError(
                    f"OQI2 Finding {finding_id} has no ACTIVE correspondence"
                )
            members = sorted(correspondence.members, key=lambda member: member.participant_role)
            return ResolvedFindingSubject(
                finding_state_revision=comparison_finding_model.state_revision,
                source_object_ids=tuple(member.source_object_id for member in members),
                source_record_references=tuple(
                    member.source_record_reference for member in members
                ),
            )
        raise AssertionError(f"unreachable: unknown finding_family {finding_family!r}")

    # ------------------------------------------------------------------
    # Direct impact (CDD-042 §4.3, §4.6, §6) -- consumes
    # EntityResolutionStore; creates zero resolution records.
    # ------------------------------------------------------------------

    def resolve_direct_impact(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]
    ) -> DirectImpactResult:
        store = EntityResolutionStore(self.session)
        records = [
            store.get_current_record(
                tenant_id, EntityResolutionStore.understanding_key((source_object_id,))
            )
            for source_object_id in source_object_ids
        ]
        if len(source_object_ids) == 1:
            record = records[0]
            if record is None:
                return DirectImpactResult(ImpactOutcome.IMPACT_UNKNOWN, None, None)
            if record.outcome == "Resolved" and record.enterprise_entity_id is not None:
                return DirectImpactResult(
                    ImpactOutcome.IMPACTED, record.record_id, record.enterprise_entity_id
                )
            if record.outcome in ("Unresolved", "Blocked Conflict"):
                return DirectImpactResult(ImpactOutcome.NO_IMPACT, record.record_id, None)
            return DirectImpactResult(ImpactOutcome.IMPACT_UNKNOWN, record.record_id, None)

        # CDD-042 §4.6: OQI2 N-participant case. Never pick a canonical
        # entity among disagreeing participants (majority/authority-as-
        # truth firewall) -- disagreement resolves to IMPACT_UNKNOWN.
        resolved = [
            record
            for record in records
            if record is not None
            and record.outcome == "Resolved"
            and record.enterprise_entity_id is not None
        ]
        distinct_entities = {record.enterprise_entity_id for record in resolved}
        if not distinct_entities:
            return DirectImpactResult(ImpactOutcome.IMPACT_UNKNOWN, None, None)
        if len(distinct_entities) > 1:
            return DirectImpactResult(ImpactOutcome.IMPACT_UNKNOWN, None, None)
        entity_id = next(iter(distinct_entities))
        winner = min(resolved, key=lambda record: str(record.record_id))
        return DirectImpactResult(ImpactOutcome.IMPACTED, winner.record_id, entity_id)

    # ------------------------------------------------------------------
    # Propagation (CDD-042 §9) -- single recursive CTE statement.
    # ------------------------------------------------------------------

    def traverse_propagation(
        self,
        *,
        tenant_id: str,
        direct_entity_id: UUID,
        _test_only_delay_seconds: float | None = None,
    ) -> tuple[PropagatedPathCandidate, ...]:
        """CDD-042 §9: institutional relationships AND the ACTIVE
        propagation-policy set are read inside this one statement's one
        READ COMMITTED snapshot -- never a separate policy pre-query. Tenant
        is re-applied at the anchor and at every recursive step (never only
        the seed). Cycle safety via a `visited` array carried through the
        recursive term; recursion for a branch terminates the instant a
        node would re-enter its own path. `_test_only_delay_seconds` is a
        repository-internal test seam (zero effect on any production
        caller, which never supplies it) proving the statement's snapshot
        is genuinely fixed at its start regardless of how long it later
        takes to finish -- the exact technique already proven sound for
        CDD-041's evidence-frontier writer-during-statement test."""
        delay_join = ""
        params: dict[str, object] = {
            "tenant_id": tenant_id,
            "direct_entity_id": direct_entity_id,
            "global_ceiling": GLOBAL_MAX_DEPTH_CEILING,
        }
        if _test_only_delay_seconds is not None:
            delay_join = "CROSS JOIN (SELECT pg_sleep(:test_delay)) AS delay_gate"
            params["test_delay"] = _test_only_delay_seconds

        stmt = text(
            f"""
            WITH RECURSIVE active_policies AS (
                SELECT policy_id, relationship_type_id, direction, max_depth, version_number
                FROM impact_propagation_policies
                WHERE tenant_id = :tenant_id AND governance_status = 'Active'
            ),
            traversable_edges AS (
                SELECT
                    ir.institutional_relationship_id AS rel_id,
                    ir.from_entity_id AS src,
                    ir.to_entity_id AS dst,
                    ap.policy_id AS policy_id,
                    ap.version_number AS policy_version,
                    ap.max_depth AS max_depth,
                    'FORWARD' AS traversal_direction
                FROM institutional_relationships ir
                JOIN active_policies ap ON ap.relationship_type_id = ir.relationship_type_id
                WHERE ir.tenant_id = :tenant_id AND ap.direction IN ('FORWARD', 'BOTH')
                UNION ALL
                SELECT
                    ir.institutional_relationship_id AS rel_id,
                    ir.to_entity_id AS src,
                    ir.from_entity_id AS dst,
                    ap.policy_id AS policy_id,
                    ap.version_number AS policy_version,
                    ap.max_depth AS max_depth,
                    'REVERSE' AS traversal_direction
                FROM institutional_relationships ir
                JOIN active_policies ap ON ap.relationship_type_id = ir.relationship_type_id
                WHERE ir.tenant_id = :tenant_id AND ap.direction IN ('REVERSE', 'BOTH')
            ),
            traversal AS (
                SELECT
                    CAST(:direct_entity_id AS uuid) AS entity_id,
                    0 AS depth,
                    ARRAY[CAST(:direct_entity_id AS uuid)]::uuid[] AS visited,
                    ARRAY[]::uuid[] AS rel_path,
                    ARRAY[]::uuid[] AS policy_path,
                    ARRAY[]::integer[] AS policy_version_path,
                    ARRAY[]::text[] AS dir_path
                UNION ALL
                SELECT
                    te.dst,
                    t.depth + 1,
                    t.visited || te.dst,
                    t.rel_path || te.rel_id,
                    t.policy_path || te.policy_id,
                    t.policy_version_path || te.policy_version,
                    t.dir_path || te.traversal_direction
                FROM traversal t
                JOIN traversable_edges te ON te.src = t.entity_id
                WHERE t.depth < te.max_depth
                  AND t.depth < :global_ceiling
                  AND NOT (te.dst = ANY(t.visited))
            )
            SELECT entity_id, depth, rel_path, policy_path, policy_version_path, dir_path
            FROM traversal
            {delay_join}
            WHERE depth > 0
            """
        )
        rows = self.session.execute(stmt, params).all()
        return tuple(
            PropagatedPathCandidate(
                entity_id=row.entity_id,
                depth=row.depth,
                relationship_ids=tuple(row.rel_path),
                policy_ids=tuple(row.policy_path),
                policy_versions=tuple(row.policy_version_path),
                directions=tuple(row.dir_path),
            )
            for row in rows
        )

    # ------------------------------------------------------------------
    # Persistence (CDD-042 §11, §14) -- parent-gated idempotent insert;
    # no independent per-child conflict handling (CDD-041's proven rule,
    # reused verbatim).
    # ------------------------------------------------------------------

    def insert_evaluation_idempotent(self, evaluation: OntologyImpactEvaluation) -> bool:
        parent_row = OntologyImpactEvaluationORM(
            evaluation_id=evaluation.evaluation_id,
            tenant_id=evaluation.tenant_id,
            finding_family=evaluation.finding_family.value,
            finding_id=evaluation.finding_id,
            finding_state_revision=evaluation.finding_state_revision,
            outcome=evaluation.outcome.value,
            resolution_record_id=evaluation.resolution_record_id,
            traversed_state_digest=evaluation.traversed_state_digest,
            evaluated_at=evaluation.evaluated_at,
        )
        parent_values = {
            column.name: getattr(parent_row, column.name)
            for column in OntologyImpactEvaluationORM.__table__.columns
        }
        insert_stmt = (
            pg_insert(OntologyImpactEvaluationORM)
            .values(**parent_values)
            .on_conflict_do_nothing(index_elements=["evaluation_id"])
            .returning(OntologyImpactEvaluationORM.evaluation_id)
        )
        won_ownership = self.session.execute(insert_stmt).first() is not None
        if not won_ownership:
            return False

        self.session.flush()
        for observation in evaluation.observations:
            self.session.add(
                OntologyImpactObservationORM(
                    evaluation_id=evaluation.evaluation_id,
                    ontology_element_type=observation.ontology_element_type.value,
                    ontology_element_id=observation.ontology_element_id,
                    impact_kind=observation.impact_kind.value,
                    basis=observation.basis.value,
                    depth=observation.depth,
                )
            )
        self.session.flush()
        for path in evaluation.paths:
            self.session.add(
                OntologyImpactPathORM(
                    evaluation_id=evaluation.evaluation_id,
                    ontology_element_id=path.ontology_element_id,
                    path_ordinal=path.path_ordinal,
                    institutional_relationship_id=path.institutional_relationship_id,
                    direction=path.direction,
                    policy_id=path.policy_id,
                    policy_version_number=path.policy_version_number,
                )
            )
        self.session.flush()
        return True

    def upsert_current_impact(self, current_impact: CurrentOntologyImpact) -> None:
        """CDD-042 §14: only ever called by the transaction that won
        `insert_evaluation_idempotent`'s ownership race -- a plain
        natural-key upsert with no independent race window, requiring no
        new advisory-lock seed."""
        model = self.session.get(CurrentOntologyImpactORM, current_impact.current_impact_id)
        if model is None:
            self.session.add(
                CurrentOntologyImpactORM(
                    current_impact_id=current_impact.current_impact_id,
                    tenant_id=current_impact.tenant_id,
                    finding_family=current_impact.finding_family.value,
                    finding_id=current_impact.finding_id,
                    ontology_element_type=current_impact.ontology_element_type.value,
                    ontology_element_id=current_impact.ontology_element_id,
                    impact_kind=current_impact.impact_kind.value,
                    status=current_impact.status.value,
                    latest_evaluation_id=current_impact.latest_evaluation_id,
                    first_seen_at=current_impact.first_seen_at,
                    last_seen_at=current_impact.last_seen_at,
                )
            )
            return
        model.status = current_impact.status.value
        model.latest_evaluation_id = current_impact.latest_evaluation_id
        model.last_seen_at = current_impact.last_seen_at

    def get_current_impacts_for_finding(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> tuple[CurrentOntologyImpact, ...]:
        from sqlalchemy import select

        rows = self.session.scalars(
            select(CurrentOntologyImpactORM).where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.finding_family == finding_family.value,
                CurrentOntologyImpactORM.finding_id == finding_id,
            )
        ).all()
        return tuple(
            CurrentOntologyImpact(
                current_impact_id=row.current_impact_id,
                tenant_id=row.tenant_id,
                finding_family=FindingFamily(row.finding_family),
                finding_id=row.finding_id,
                ontology_element_type=OntologyElementType(row.ontology_element_type),
                ontology_element_id=row.ontology_element_id,
                impact_kind=ImpactClass(row.impact_kind),
                status=CurrentImpactStatus(row.status),
                latest_evaluation_id=row.latest_evaluation_id,
                first_seen_at=row.first_seen_at,
                last_seen_at=row.last_seen_at,
            )
            for row in rows
        )

    def get_current_impacts_for_subject(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> tuple[CurrentOntologyImpact, ...]:
        """CDD-044 §49 (OQI6 Artifact Authorization §2.2 row 11): narrow,
        additive, read-only. Returns every `CurrentOntologyImpact` row
        naming this ontology subject, across every Finding that resolved
        to it -- OQI6's own subject-level Reliance/Business-Impact
        derivation, never a write path, never a change to any existing
        method's behavior."""
        from sqlalchemy import select

        rows = self.session.scalars(
            select(CurrentOntologyImpactORM).where(
                CurrentOntologyImpactORM.tenant_id == tenant_id,
                CurrentOntologyImpactORM.ontology_element_type == ontology_element_type.value,
                CurrentOntologyImpactORM.ontology_element_id == ontology_element_id,
            )
        ).all()
        return tuple(
            CurrentOntologyImpact(
                current_impact_id=row.current_impact_id,
                tenant_id=row.tenant_id,
                finding_family=FindingFamily(row.finding_family),
                finding_id=row.finding_id,
                ontology_element_type=OntologyElementType(row.ontology_element_type),
                ontology_element_id=row.ontology_element_id,
                impact_kind=ImpactClass(row.impact_kind),
                status=CurrentImpactStatus(row.status),
                latest_evaluation_id=row.latest_evaluation_id,
                first_seen_at=row.first_seen_at,
                last_seen_at=row.last_seen_at,
            )
            for row in rows
        )

    def get_evaluation(self, evaluation_id: UUID) -> OntologyImpactEvaluation | None:
        model = self.session.get(OntologyImpactEvaluationORM, evaluation_id)
        if model is None:
            return None
        observation_rows = self.session.execute(
            OntologyImpactObservationORM.__table__.select().where(
                OntologyImpactObservationORM.evaluation_id == evaluation_id
            )
        ).all()
        path_rows = self.session.execute(
            OntologyImpactPathORM.__table__.select().where(
                OntologyImpactPathORM.evaluation_id == evaluation_id
            )
        ).all()
        observations = tuple(
            OntologyImpactObservation(
                ontology_element_type=OntologyElementType(row.ontology_element_type),
                ontology_element_id=row.ontology_element_id,
                impact_kind=ImpactClass(row.impact_kind),
                basis=ImpactBasis(row.basis),
                depth=row.depth,
            )
            for row in observation_rows
        )
        paths = tuple(
            OntologyImpactPath(
                ontology_element_id=row.ontology_element_id,
                path_ordinal=row.path_ordinal,
                institutional_relationship_id=row.institutional_relationship_id,
                direction=row.direction,
                policy_id=row.policy_id,
                policy_version_number=row.policy_version_number,
            )
            for row in path_rows
        )
        return OntologyImpactEvaluation(
            evaluation_id=model.evaluation_id,
            tenant_id=model.tenant_id,
            finding_family=FindingFamily(model.finding_family),
            finding_id=model.finding_id,
            finding_state_revision=model.finding_state_revision,
            outcome=ImpactOutcome(model.outcome),
            resolution_record_id=model.resolution_record_id,
            traversed_state_digest=model.traversed_state_digest,
            evaluated_at=model.evaluated_at,
            observations=observations,
            paths=paths,
        )
