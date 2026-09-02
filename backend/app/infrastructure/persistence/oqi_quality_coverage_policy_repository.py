"""Repository for OQI-H1 `QualityCoveragePolicy` persistence and
generalized coverage derivation (CDD-047 §8-§17; Artifact Authorization
row 4).

`compute_generalized_coverage` is the single integration point
`oqi_business_impact_repository.py` calls (Artifact Authorization row 12).
Its no-policy branch returns the caller's own, unmodified legacy
coverage value verbatim -- CDD-047 §16/§18's backward-compatibility
identity requirement -- never re-deriving it independently.

Relationship-anchor fail-closed behavior (CDD-047 §15) is made explicit
here, not left as an emergent property of empty-tuple guards buried in
per-dimension queries: an empty `source_object_ids` tuple (which is
exactly what the caller already passes for a RELATIONSHIP subject, per
`compute_subject_finding_state`'s own existing, unmodified branch) short-
circuits every required dimension to uncovered before any query runs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_quality_coverage.policy import (
    CoverageDimension,
    QualityCoveragePolicy,
    QualityCoveragePolicyStatus,
)
from app.infrastructure.persistence.models.oqi_quality_coverage_policy import (
    QualityCoveragePolicyDimensionORM,
    QualityCoveragePolicyORM,
)
from app.infrastructure.persistence.oqi_accuracy_evaluation_repository import (
    OqiAccuracyEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_business_rule_evaluation_repository import (
    OqiBusinessRuleEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_conformity_evaluation_repository import (
    OqiConformityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_cross_source_evaluation_repository import (
    OqiCrossSourceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)

#: CDD-047 §11, Artifact Authorization §4: distinct from every existing
#: OQI advisory-lock seed (1=OQI1, 2=OQI2, 3=OQI3, 4=OQI6) -- the exactly
#: one new seed value this document's Artifact Authorization reserves.
OQI_QUALITY_COVERAGE_ADVISORY_LOCK_SEED = 5

#: CDD-047 §14: only these two OQI1 dimensions have a live evaluator whose
#: coverage this repository can prove from persisted evidence.
_OQI1_DIMENSIONS = frozenset({CoverageDimension.COMPLETENESS, CoverageDimension.VALIDITY})


class OqiQualityCoveragePolicyRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Advisory lock (CDD-047 §11, dedicated seed 5).
    # ------------------------------------------------------------------

    def acquire_policy_authority(self, identity: str) -> None:
        """Transaction-scoped: releases automatically on COMMIT, ROLLBACK,
        or connection loss. Serializes the read-latest-version-then-insert-
        next-version sequence for one logical policy (tenant + anchor)
        against concurrent callers -- the database's own partial
        ACTIVE-uniqueness index (CDD-047 §11) remains the actual safety
        guarantee regardless; this lock only prevents two concurrent
        callers from computing the same next `version_number`."""
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_QUALITY_COVERAGE_ADVISORY_LOCK_SEED},
        )

    # ------------------------------------------------------------------
    # Policy persistence.
    # ------------------------------------------------------------------

    def insert_policy(self, policy: QualityCoveragePolicy) -> None:
        """A plain insert -- policy versions are immutable, never upserted.
        The database's partial unique index is the actual enforcement of
        "at most one ACTIVE version per (tenant, anchor)" (CDD-047 §11);
        this method does not pre-check for an existing ACTIVE row, so a
        violation surfaces as a real `IntegrityError` from Postgres, never
        a silently swallowed duplicate."""
        self.session.add(
            QualityCoveragePolicyORM(
                policy_id=policy.policy_id,
                tenant_id=policy.tenant_id,
                ontology_element_type=policy.ontology_element_type.value,
                ontology_element_id=policy.ontology_element_id,
                status=policy.status.value,
                version_number=policy.version_number,
                previous_version_id=policy.previous_version_id,
                created_by=policy.created_by,
                created_on=policy.created_on,
            )
        )
        self.session.flush()
        for dimension in sorted(policy.required_dimensions, key=lambda d: d.value):
            self.session.add(
                QualityCoveragePolicyDimensionORM(
                    policy_id=policy.policy_id, dimension=dimension.value
                )
            )
        self.session.flush()

    def get_latest_policy_version(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> QualityCoveragePolicy | None:
        """Tenant-scoped. Returns the highest-`version_number` row for this
        anchor regardless of status -- callers wanting only a governing
        policy must use `get_active_policy`."""
        model = (
            self.session.query(QualityCoveragePolicyORM)
            .filter(
                QualityCoveragePolicyORM.tenant_id == tenant_id,
                QualityCoveragePolicyORM.ontology_element_type == ontology_element_type.value,
                QualityCoveragePolicyORM.ontology_element_id == ontology_element_id,
            )
            .order_by(QualityCoveragePolicyORM.version_number.desc())
            .first()
        )
        return None if model is None else self._to_domain(model)

    def get_active_policy(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> QualityCoveragePolicy | None:
        """Tenant-scoped. Returns the single `ACTIVE` version for this
        anchor if one exists, else `None` -- `None` is the correct,
        unambiguous "no active policy" signal that routes
        `compute_generalized_coverage` to CDD-047 §16's legacy-identity
        branch. A genuine query/computation failure must raise, never be
        interpreted as `None` (CDD-047 §14 of the governing prompt)."""
        model = (
            self.session.query(QualityCoveragePolicyORM)
            .filter(
                QualityCoveragePolicyORM.tenant_id == tenant_id,
                QualityCoveragePolicyORM.ontology_element_type == ontology_element_type.value,
                QualityCoveragePolicyORM.ontology_element_id == ontology_element_id,
                QualityCoveragePolicyORM.status == QualityCoveragePolicyStatus.ACTIVE.value,
            )
            .one_or_none()
        )
        return None if model is None else self._to_domain(model)

    def _to_domain(self, model: QualityCoveragePolicyORM) -> QualityCoveragePolicy:
        dimension_rows = (
            self.session.execute(
                select(QualityCoveragePolicyDimensionORM.dimension).where(
                    QualityCoveragePolicyDimensionORM.policy_id == model.policy_id
                )
            )
            .scalars()
            .all()
        )
        return QualityCoveragePolicy(
            policy_id=model.policy_id,
            tenant_id=model.tenant_id,
            ontology_element_type=OntologyElementType(model.ontology_element_type),
            ontology_element_id=model.ontology_element_id,
            status=QualityCoveragePolicyStatus(model.status),
            version_number=model.version_number,
            previous_version_id=model.previous_version_id,
            required_dimensions=frozenset(CoverageDimension(value) for value in dimension_rows),
            created_by=model.created_by,
            created_on=model.created_on,
        )

    # ------------------------------------------------------------------
    # Generalized coverage derivation (CDD-047 §13-§17).
    # ------------------------------------------------------------------

    def compute_generalized_coverage(
        self,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
        source_object_ids: tuple[UUID, ...],
        legacy_any_evaluation_ever_run: bool,
    ) -> bool:
        """CDD-047 §13. No-policy branch returns
        `legacy_any_evaluation_ever_run` verbatim -- the identical value
        the caller's own existing `_compute_coverage`-derived computation
        already produced, unmodified (CDD-047 §16, §18's backward-
        compatibility proof depends on this being a literal pass-through,
        never a re-derivation)."""
        active_policy = self.get_active_policy(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            ontology_element_id=ontology_element_id,
        )
        if active_policy is None:
            return legacy_any_evaluation_ever_run

        if not source_object_ids:
            # CDD-047 §15: no evidence-resolution mechanism exists for a
            # RELATIONSHIP-anchored subject (or any subject with no
            # resolvable source objects) -- every required dimension is
            # uncovered, explicitly, before any dimension query runs.
            return False

        for dimension in active_policy.required_dimensions:
            if not self.has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id,
                source_object_ids=source_object_ids,
                dimension=dimension,
            ):
                return False
        return True

    def has_qualifying_coverage_for_dimension(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...], dimension: CoverageDimension
    ) -> bool:
        """CDD-047 §14: dispatch across the closed `CoverageDimension`
        vocabulary. Only COMPLETENESS/VALIDITY (OQI1) and CONSISTENCY
        (OQI2) route to a real evaluator query -- the remaining six
        dimensions have no live evaluator and return `False`
        unconditionally, a structural fact, never a computed negative."""
        if dimension in _OQI1_DIMENSIONS:
            return OqiQualityEvaluationRepositoryImpl(
                self.session
            ).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=source_object_ids, dimension=dimension.value
            )
        if dimension is CoverageDimension.CONSISTENCY:
            return OqiCrossSourceEvaluationRepositoryImpl(
                self.session
            ).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=source_object_ids, dimension=dimension.value
            )
        # CDD-048 §23: ACCURACY is OQI1-storage-shaped (same evaluation
        # ledger, dimension=ACCURACY) -- reuses the identically-shaped
        # accuracy repository method.
        if dimension is CoverageDimension.ACCURACY:
            return OqiAccuracyEvaluationRepositoryImpl(
                self.session
            ).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=source_object_ids, dimension=dimension.value
            )
        # CDD-048 §23: REASONABLENESS is OQI3-storage-shaped (BusinessRule
        # dimension tag) -- reuses the identically-shaped business-rule
        # evaluation repository method.
        if dimension is CoverageDimension.REASONABLENESS:
            return OqiBusinessRuleEvaluationRepositoryImpl(
                self.session
            ).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=source_object_ids, dimension=dimension.value
            )
        # CDD-049 §21: CONFORMITY is OQI1-storage-shaped (same evaluation
        # ledger, dimension=CONFORMITY) -- reuses the identically-shaped
        # conformity repository method. NO_STANDARD/NOT_MAPPED/AMBIGUOUS
        # all produce zero persisted evaluation rows (CDD-049 §14), so this
        # query structurally returns False for those cases without any
        # special-casing here.
        if dimension is CoverageDimension.CONFORMITY:
            return OqiConformityEvaluationRepositoryImpl(
                self.session
            ).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=source_object_ids, dimension=dimension.value
            )
        # UNIQUENESS, TIMELINESS, INTEGRITY: no evaluator exists (CDD-047
        # §14, unchanged). Never query, never infer, never synthesize --
        # unconditionally uncovered.
        return False
