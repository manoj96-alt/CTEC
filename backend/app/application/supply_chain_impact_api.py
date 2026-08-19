"""Gate F traversal orchestration (CDD-015 §8, §14, §33; remediated per the
merged Gate F Governed Impact Decision Policy Clarification and
Remediation Report, PR #69). The internal application-layer entry point
for one governed Gate F evaluation.

Loads the tenant graph once and calls the existing, unmodified
`find_paths_to_target_type` once per chain segment (Supplier -> Material ->
Product/BOM -> Facility, Product -> Revenue Exposure, Supplier -> Region ->
Risk Event), then hands the results to the §9-§12 adapters
(`integration/adapters/gate_f/`).

The request identifies only the evaluation target (which Supplier).
Alternate-supplier candidates are discovered internally from governed
tenant state, never supplied by the caller; qualification, capacity, lead
time, cost, disruption severity, and sourcing concentration are all
derived/read from governed CTEC state by the adapters -- no external
request field is ever authoritative for a decision-relevant fact. Tenant
identity is sourced exclusively from the caller-supplied `TrustedPrincipal`
(PAD-003 §8), the same pattern `application/ontology_copilot_api.py`
already uses.

Callable without HTTP -- no FastAPI route is defined here (F-I2 stops
before the HTTP/security boundary). Never invokes ERM/SRM/ASM, never
mutates `domain/ontology_copilot/traversal.py` or
`application/ontology_copilot_api.py`, and never persists a traversal
result as a new canonical artifact (CDD-015 §28 acceptance criterion 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.domain.decision_engine import DecisionEvaluationGroupModel
from app.domain.decision_engine.configuration import (
    GateFPolicyConfiguration,
    load_gate_f_policy_configuration,
)
from app.domain.ontology_copilot.traversal import (
    GraphEdge,
    GraphEntity,
    TraversalPath,
    find_paths_to_target_type,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.decision_repository import DecisionEvaluationRepositoryImpl
from app.infrastructure.persistence.institutional_relationship_store import (
    InstitutionalRelationshipStore,
)
from app.integration.adapters.gate_f.drm import DrmUnit
from app.integration.gate_f_pipeline import gate_f_capability_adapters

SUPPLIER_ENTITY_TYPE_NAME = "Supplier"
MATERIAL_ENTITY_TYPE_NAME = "Material"
PRODUCT_ENTITY_TYPE_NAME = "Product"
FACILITY_ENTITY_TYPE_NAME = "Facility"
REVENUE_EXPOSURE_ENTITY_TYPE_NAME = "Revenue Exposure"
REGION_ENTITY_TYPE_NAME = "Region"
RISK_EVENT_ENTITY_TYPE_NAME = "Risk Event"
ALTERNATE_SUPPLIER_ENTITY_TYPE_NAME = "Alternate Supplier"

_SUPPLIER_TO_MATERIAL_DEPTH = 1
_MATERIAL_TO_PRODUCT_DEPTH = 2
_PRODUCT_TO_FACILITY_DEPTH = 1
_PRODUCT_TO_REVENUE_EXPOSURE_DEPTH = 1
_SUPPLIER_TO_RISK_EVENT_DEPTH = 2


@dataclass(frozen=True, slots=True)
class SupplyChainImpactEvaluateRequest:
    """The evaluation target only -- CDD-015-authorized request context.
    No qualification/capacity/lead-time/cost/severity/sourcing field is
    accepted here: those are governed facts the evaluation itself derives
    from CTEC state (merged clarification Amendment R)."""

    supplier_entity_id: UUID


@dataclass(frozen=True, slots=True)
class ImpactedMaterial:
    material_entity_id: UUID
    material_name: str
    path: TraversalPath
    revenue_exposure_entity_id: UUID | None


@dataclass(frozen=True, slots=True)
class ImpactedEntity:
    entity_id: UUID
    entity_name: str


@dataclass(frozen=True, slots=True)
class ImpactSummary:
    supplier_entity_id: UUID
    supplier_name: str
    materials: tuple[ImpactedMaterial, ...]
    products: tuple[ImpactedEntity, ...]
    facilities: tuple[ImpactedEntity, ...]
    revenue_exposures: tuple[ImpactedEntity, ...]


@dataclass(frozen=True, slots=True)
class CandidateOutcome:
    alternate_supplier_entity_id: UUID | None
    outcome: str | None
    reason: str | None
    decision_record_identifier: UUID | None


@dataclass(frozen=True, slots=True)
class MaterialEvaluationResult:
    material_entity_id: UUID
    high_severity_disruption: bool | None
    single_source_exposure: bool | None
    revenue_materiality: bool | None
    candidates: tuple[CandidateOutcome, ...]


@dataclass(frozen=True, slots=True)
class SupplyChainImpactEvaluationResult:
    """Decision Evaluation identity, impact summary, per-material governed
    conditions and candidate outcomes, and governance state -- CDD-015
    §21's typed evaluate output, before any HTTP/API projection (F-I3+)."""

    decision_evaluation_id: UUID
    tenant_id: str
    impact: ImpactSummary
    materials: tuple[MaterialEvaluationResult, ...]
    governance_standing: str | None
    governance_record_identifier: UUID | None


class SupplyChainImpactApiService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        *,
        policy: GateFPolicyConfiguration | None = None,
    ) -> None:
        self._sessions = sessions
        self._policy = policy or load_gate_f_policy_configuration()

    def evaluate(
        self, principal: TrustedPrincipal, request: SupplyChainImpactEvaluateRequest
    ) -> SupplyChainImpactEvaluationResult:
        tenant_id = principal.tenant_id
        now = datetime.now(UTC)
        session = self._sessions()
        try:
            result = self._evaluate(session, tenant_id, now, request)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _evaluate(
        self,
        session: Session,
        tenant_id: str,
        now: datetime,
        request: SupplyChainImpactEvaluateRequest,
    ) -> SupplyChainImpactEvaluationResult:
        store = InstitutionalRelationshipStore(session)
        entities_by_id, edges = store.load_tenant_graph(tenant_id)

        supplier = entities_by_id.get(request.supplier_entity_id)
        if supplier is None or supplier.entity_type_name != SUPPLIER_ENTITY_TYPE_NAME:
            raise ValidationException("Supplier does not exist for this tenant")

        impact = self._traverse_impact(supplier, entities_by_id, edges)
        risk_event_entity_id = self._find_risk_event(supplier, entities_by_id, edges)
        alternate_supplier_ids = tuple(
            sorted(
                (
                    entity.entity_id
                    for entity in entities_by_id.values()
                    if entity.entity_type_name == ALTERNATE_SUPPLIER_ENTITY_TYPE_NAME
                ),
                key=str,
            )
        )

        decision_evaluation_id = uuid4()
        DecisionEvaluationRepositoryImpl(session).create_group(
            DecisionEvaluationGroupModel(
                decision_evaluation_id=decision_evaluation_id,
                tenant_id=tenant_id,
                created_at=now,
            )
        )
        session.flush()

        adapters = gate_f_capability_adapters(session)
        high_severity = adapters.krm.derive_high_severity_disruption(
            risk_event_entity_id=risk_event_entity_id
        )

        material_results: list[MaterialEvaluationResult] = []
        any_decision_recorded = False
        for material in impact.materials:
            single_source = adapters.krm.derive_single_source_exposure(
                tenant_id=tenant_id, material_entity_id=material.material_entity_id, now=now
            )
            revenue_materiality = adapters.krm.derive_revenue_materiality(
                revenue_exposure_entity_id=material.revenue_exposure_entity_id,
                threshold_usd=self._policy.materiality_threshold_usd,
            )

            candidates: list[CandidateOutcome] = []
            targets = alternate_supplier_ids or (None,)
            for alternate_supplier_entity_id in targets:
                candidate_evidence = (
                    adapters.krm.derive_candidate_evidence(
                        tenant_id=tenant_id,
                        alternate_supplier_entity_id=alternate_supplier_entity_id,
                        material_entity_id=material.material_entity_id,
                        now=now,
                    )
                    if alternate_supplier_entity_id is not None
                    else None
                )
                unit = DrmUnit(
                    material_entity_id=material.material_entity_id,
                    alternate_supplier_entity_id=alternate_supplier_entity_id,
                    high_severity_disruption=high_severity,
                    single_source_exposure=single_source,
                    revenue_materiality=revenue_materiality,
                    candidate=candidate_evidence,
                )
                decision = adapters.drm.evaluate(
                    decision_evaluation_id=decision_evaluation_id,
                    unit=unit,
                    policy=self._policy,
                    now=now,
                )
                if decision is None:
                    candidates.append(
                        CandidateOutcome(alternate_supplier_entity_id, None, None, None)
                    )
                    continue
                any_decision_recorded = True
                candidates.append(
                    CandidateOutcome(
                        alternate_supplier_entity_id,
                        decision.outcome.value,
                        decision.reason.value,
                        decision.record_identifier,
                    )
                )

            material_results.append(
                MaterialEvaluationResult(
                    material_entity_id=material.material_entity_id,
                    high_severity_disruption=high_severity.value,
                    single_source_exposure=single_source.value,
                    revenue_materiality=revenue_materiality.value,
                    candidates=tuple(candidates),
                )
            )

        governance_standing: str | None = None
        governance_record_identifier: UUID | None = None
        if any_decision_recorded:
            governance_result = adapters.grm.evaluate(
                decision_evaluation_id=decision_evaluation_id, now=now
            )
            governance_standing = governance_result.standing.value
            governance_record_identifier = governance_result.record_identifier

        return SupplyChainImpactEvaluationResult(
            decision_evaluation_id=decision_evaluation_id,
            tenant_id=tenant_id,
            impact=impact,
            materials=tuple(material_results),
            governance_standing=governance_standing,
            governance_record_identifier=governance_record_identifier,
        )

    @staticmethod
    def _find_risk_event(
        supplier: GraphEntity,
        entities_by_id: dict[UUID, GraphEntity],
        edges: tuple[GraphEdge, ...],
    ) -> UUID | None:
        paths = find_paths_to_target_type(
            start_entity=supplier,
            entities_by_id=entities_by_id,
            edges=edges,
            target_entity_type_name=RISK_EVENT_ENTITY_TYPE_NAME,
            max_depth=_SUPPLIER_TO_RISK_EVENT_DEPTH,
        )
        return paths[0].target_entity_id if paths else None

    @staticmethod
    def _traverse_impact(
        supplier: GraphEntity,
        entities_by_id: dict[UUID, GraphEntity],
        edges: tuple[GraphEdge, ...],
    ) -> ImpactSummary:
        material_paths = find_paths_to_target_type(
            start_entity=supplier,
            entities_by_id=entities_by_id,
            edges=edges,
            target_entity_type_name=MATERIAL_ENTITY_TYPE_NAME,
            max_depth=_SUPPLIER_TO_MATERIAL_DEPTH,
        )

        products: dict[UUID, ImpactedEntity] = {}
        facilities: dict[UUID, ImpactedEntity] = {}
        revenue_exposures: dict[UUID, ImpactedEntity] = {}
        materials: list[ImpactedMaterial] = []
        for path in material_paths:
            material_entity = entities_by_id[path.target_entity_id]
            product_paths = find_paths_to_target_type(
                start_entity=material_entity,
                entities_by_id=entities_by_id,
                edges=edges,
                target_entity_type_name=PRODUCT_ENTITY_TYPE_NAME,
                max_depth=_MATERIAL_TO_PRODUCT_DEPTH,
            )
            material_revenue_exposure_entity_id: UUID | None = None
            for product_path in product_paths:
                products[product_path.target_entity_id] = ImpactedEntity(
                    product_path.target_entity_id, product_path.target_entity_name
                )
                product_entity = entities_by_id[product_path.target_entity_id]
                for facility_path in find_paths_to_target_type(
                    start_entity=product_entity,
                    entities_by_id=entities_by_id,
                    edges=edges,
                    target_entity_type_name=FACILITY_ENTITY_TYPE_NAME,
                    max_depth=_PRODUCT_TO_FACILITY_DEPTH,
                ):
                    facilities[facility_path.target_entity_id] = ImpactedEntity(
                        facility_path.target_entity_id, facility_path.target_entity_name
                    )
                for revenue_path in find_paths_to_target_type(
                    start_entity=product_entity,
                    entities_by_id=entities_by_id,
                    edges=edges,
                    target_entity_type_name=REVENUE_EXPOSURE_ENTITY_TYPE_NAME,
                    max_depth=_PRODUCT_TO_REVENUE_EXPOSURE_DEPTH,
                ):
                    revenue_exposures[revenue_path.target_entity_id] = ImpactedEntity(
                        revenue_path.target_entity_id, revenue_path.target_entity_name
                    )
                    if material_revenue_exposure_entity_id is None:
                        material_revenue_exposure_entity_id = revenue_path.target_entity_id

            materials.append(
                ImpactedMaterial(
                    material_entity_id=path.target_entity_id,
                    material_name=path.target_entity_name,
                    path=path,
                    revenue_exposure_entity_id=material_revenue_exposure_entity_id,
                )
            )

        return ImpactSummary(
            supplier_entity_id=supplier.entity_id,
            supplier_name=supplier.entity_name,
            materials=tuple(materials),
            products=tuple(products.values()),
            facilities=tuple(facilities.values()),
            revenue_exposures=tuple(revenue_exposures.values()),
        )
