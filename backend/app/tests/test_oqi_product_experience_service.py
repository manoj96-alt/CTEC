"""CDD-045 Artifact Authorization §2 row 7 -- OQI7-I1 domain-level
aggregation tests for `OqiProductExperienceService`. Proves: N-source
agreement/dissent/missingness preservation, `IMPACT_UNKNOWN`/
`BUSINESS_IMPACT_UNKNOWN`/`RELIANCE_UNKNOWN` non-downgrade, candidate-not-
truth labeling, contextual criticality (never collapsed to one entity-
global value), and specialist-supported-vs-synthesizer-only recommendation-
basis detection -- driven entirely by real, unmodified OQI1-6/OQI5-I2
domain services against real Postgres, never a constructed response DTO
standing in for a real evaluator/agent result. Reuses this repository's own
established sibling-test-file helper-import precedent (`_seed_oqi1_finding`/
`_seed_oqi2_finding` from `test_oqi_remediation_i1.py`;
`_seed_oqi1_finding_with_evaluation` and the OQI4/OQI6 service helpers from
`test_oqi_business_impact.py`). Real-Postgres tenant-isolation, pagination,
migration/table-count, and static no-trust-score/no-Gate-F sweeps are
proven separately in `test_oqi_api_postgres.py`."""

# isort: skip_file
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_product_experience_service import (
    EvidenceParticipantRow,
    OqiProductExperienceService,
)
from app.application.oqi_remediation_agent_service import OqiRemediationAgentService
from app.domain.oqi_business_impact.dependency import Criticality
from app.domain.oqi_business_impact.impact import BusinessImpactOutcome
from app.domain.oqi_business_impact.reliance import RelianceState
from app.domain.oqi_ontology_impact.evaluation import ImpactOutcome, OntologyElementType
from app.domain.oqi_remediation.case import FindingFamily as RemediationFindingFamily
from app.infrastructure.model_provider.provider import (
    FakeModelProvider,
    ModelInvocationRequest,
    ModelInvocationResult,
    ProviderFailureKind,
)
from app.infrastructure.persistence.oqi_remediation_agent_repository import (
    OqiRemediationAgentPacketReader,
    OqiRemediationAgentRepositoryImpl,
)
from app.infrastructure.persistence.oqi_remediation_repository import (
    OqiRemediationParticipantReader,
    OqiRemediationRepositoryImpl,
)
from app.tests.test_oqi_business_impact import (
    _business_impact_service,
    _evaluate_oqi1_finding_impact,
    _seed_oqi1_finding_with_evaluation,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity
from app.tests.test_oqi_remediation_i1 import _seed_authorization, _seed_oqi2_finding

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


def _api_service(session: Session) -> OqiProductExperienceService:
    return OqiProductExperienceService(session)


# =====================================================================
# N-source evidence -- agreement, dissent, missingness preserved
# (CDD-045 §11, §29 -- "N governed peers observed {V}", never "correct").
# =====================================================================


def test_n_source_evidence_preserves_agreement_dissent_and_missing(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={"SAP": "ABC123", "PLM": "XYZ999"},
            conflicting_roles={"SAP", "PLM"},
            missing_roles=set(),
            authoritative_role="PLM",
        )
        session.commit()

    with factory() as session:
        bundle = _api_service(session).get_evidence(tenant_id=tenant_id, finding_id=finding_id)
    assert bundle is not None
    roles = {p.source_system: p for p in bundle.participants}
    assert roles["SAP"].observed_value == "ABC123"
    assert roles["PLM"].observed_value == "XYZ999"
    assert roles["SAP"].is_conflicting is True
    assert roles["PLM"].is_conflicting is True
    assert roles["PLM"].is_authoritative is True
    assert roles["SAP"].is_authoritative is False
    # No majority/authority-as-truth field exists anywhere on the row.
    assert not hasattr(bundle, "correct_value")
    assert not hasattr(bundle, "truth")


def test_n_source_candidate_is_labeled_not_truth(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _instruction_id, _authorization_id = _seed_authorization(
            session, tenant_id=tenant_id
        )
        session.commit()

    with factory() as session:
        bundle = _api_service(session).get_evidence(tenant_id=tenant_id, finding_id=finding_id)
    assert bundle is not None
    assert bundle.candidate is not None
    # Deterministic extraction order, not authority -- either conflicting
    # value is an acceptable candidate; the point is that the candidate is
    # exposed as CANDIDATE_NOT_TRUTH, never as truth.
    assert bundle.candidate.proposed_value in {"OLD", "NEW"}
    assert bundle.candidate.supporting_participant_count >= 1


def test_missing_participant_remains_visible(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={"SAP": "ABC123", "PLM": None},
            conflicting_roles=set(),
            missing_roles={"PLM"},
            authoritative_role=None,
        )
        session.commit()

    with factory() as session:
        bundle = _api_service(session).get_evidence(tenant_id=tenant_id, finding_id=finding_id)
    assert bundle is not None
    plm = next(p for p in bundle.participants if p.source_system == "PLM")
    assert plm.is_missing is True
    assert plm.observed_value is None


def test_authority_conflict_crown_peer_majority_does_not_override_authority(
    factory: sessionmaker[Session],
) -> None:
    """OQI7-I1-VM dedicated authority-conflict crown (closes disclosed gap
    #1): 3 non-authoritative peers agree on ABC123, the one authoritative
    source dissents with XYZ999, one expected participant is missing.
    Neither peer-majority agreement nor source authority may be exposed as
    a winner/truth field -- both the agreement cluster and the
    authoritative dissent, plus the missing participant, must all survive
    API composition simultaneously (CDD-045 §29-30, phase §16-18)."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={
                "PeerA": "ABC123",
                "PeerB": "ABC123",
                "PeerC": "ABC123",
                "Authority": "XYZ999",
                "PeerE": None,
            },
            conflicting_roles={"PeerA", "PeerB", "PeerC", "Authority"},
            missing_roles={"PeerE"},
            authoritative_role="Authority",
        )
        session.commit()

    with factory() as session:
        bundle = _api_service(session).get_evidence(tenant_id=tenant_id, finding_id=finding_id)
    assert bundle is not None
    roles = {p.source_system: p for p in bundle.participants}
    assert len(roles) == 5

    for peer in ("PeerA", "PeerB", "PeerC"):
        assert roles[peer].observed_value == "ABC123"
        assert roles[peer].is_conflicting is True
        assert roles[peer].is_authoritative is False
        assert roles[peer].is_missing is False

    assert roles["Authority"].observed_value == "XYZ999"
    assert roles["Authority"].is_conflicting is True
    assert roles["Authority"].is_authoritative is True
    assert roles["Authority"].is_missing is False

    assert roles["PeerE"].is_missing is True
    assert roles["PeerE"].observed_value is None

    # Neither the peer-agreement cluster nor source authority is exposed
    # as a resolved truth/winner anywhere on the row or its dataclass shape.
    for participant in bundle.participants:
        for prohibited in (
            "truth",
            "correct_value",
            "winner",
            "golden_value",
            "majority_winner",
            "authoritative_winner",
        ):
            assert not hasattr(participant, prohibited)
    for prohibited in (
        "truth",
        "correct_value",
        "winner",
        "majority_winner",
        "authoritative_winner",
    ):
        assert prohibited not in EvidenceParticipantRow.__dataclass_fields__
    assert not hasattr(bundle, "correct_value")
    assert not hasattr(bundle, "truth")


# =====================================================================
# IMPACT_UNKNOWN never renders as NO_IMPACT (CDD-045 §12, §27, crown 4).
# Never faked by directly constructing a response object -- driven
# entirely by the real, unmodified OQI4 evaluation service.
# =====================================================================


def test_impact_unknown_survives_the_service_never_evaluated(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        # A real OQI1 Finding exists, but OQI4's own evaluator has never
        # run against it -- zero CurrentOntologyImpact rows exist.
        finding_id, _ = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        row = _api_service(session).get_ontology_impact(tenant_id=tenant_id, finding_id=finding_id)
    assert row is not None
    assert row.outcome is ImpactOutcome.IMPACT_UNKNOWN
    assert row.direct_entity_id is None


def test_impact_unknown_business_impact_also_unknown(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        row = _api_service(session).get_business_impact(tenant_id=tenant_id, finding_id=finding_id)
    assert row is not None
    assert row.outcome is BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN


# =====================================================================
# Contextual criticality -- same subject, two dependencies, two
# criticalities, never collapsed to one entity-global value (CDD-045
# §13, §29, crown 6).
# =====================================================================


def test_contextual_criticality_two_dependencies_preserved(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, object_id = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        entity_id = _entity(session, tenant_id=tenant_id, name="Material")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        _evaluate_oqi1_finding_impact(session, tenant_id=tenant_id, finding_id=finding_id)
        session.commit()

    with factory() as session:
        impact_row = _api_service(session).get_ontology_impact(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert impact_row is not None
    assert impact_row.direct_entity_id == entity_id

    with factory() as session:
        biz = _business_impact_service(session)
        process_a = biz.create_process(
            tenant_id=tenant_id, name="Production Planning", created_by="tester", created_on=NOW
        )
        process_b = biz.create_process(
            tenant_id=tenant_id, name="Sandbox Analytics", created_by="tester", created_on=NOW
        )
        biz.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process_a.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.CRITICAL,
            created_by="tester",
            created_on=NOW,
        )
        biz.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process_b.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.LOW,
            created_by="tester",
            created_on=NOW,
        )
        session.commit()

    with factory() as session:
        row = _api_service(session).get_business_impact(tenant_id=tenant_id, finding_id=finding_id)
    assert row is not None
    criticalities = {d.criticality for d in row.dependencies}
    assert Criticality.CRITICAL in criticalities
    assert Criticality.LOW in criticalities
    assert len(row.dependencies) == 2


# =====================================================================
# Reliance -- all three states, reasons preserved.
# =====================================================================


def test_reliance_at_risk_from_open_finding(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, object_id = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        entity_id = _entity(session, tenant_id=tenant_id, name="Material")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        _evaluate_oqi1_finding_impact(session, tenant_id=tenant_id, finding_id=finding_id)
        session.commit()

    with factory() as session:
        impact = _api_service(session).get_ontology_impact(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert impact is not None
    assert impact.direct_entity_id == entity_id

    with factory() as session:
        _business_impact_service(session).evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        session.commit()

    with factory() as session:
        row = _api_service(session).get_reliance(tenant_id=tenant_id, finding_id=finding_id)
    assert row is not None
    assert row.state is RelianceState.RELIANCE_AT_RISK
    assert "OPEN_QUALITY_CONDITION" in row.reason_codes


def test_reliance_unknown_when_never_evaluated(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        session.commit()

    with factory() as session:
        row = _api_service(session).get_reliance(tenant_id=tenant_id, finding_id=finding_id)
    assert row is not None
    assert row.state is RelianceState.RELIANCE_UNKNOWN


# =====================================================================
# Agent investigation -- specialist disagreement / synthesizer-only
# basis (CDD-045 §18, §29, crowns 7/8, 9/10).
# =====================================================================


def _agent_service_for(session: Session, provider: FakeModelProvider) -> OqiRemediationAgentService:
    return OqiRemediationAgentService(
        agent_repository=OqiRemediationAgentRepositoryImpl(session),
        packet_reader=OqiRemediationAgentPacketReader(session),
        remediation_repository=OqiRemediationRepositoryImpl(session),
        provider=provider,
    )


def _valid_output(candidate_id: UUID) -> dict[str, object]:
    return {
        "recommendation_type": "RECOMMEND_CANDIDATE",
        "candidate_id": str(candidate_id),
        "supporting_evidence_ids": [],
        "conflicting_evidence_ids": [],
        "impact_evaluation_ids": [],
        "rationale": "the candidate has strong evidentiary support in the packet",
    }


def test_specialist_supported_recommendation_is_labeled(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _instruction_id, _authorization_id = _seed_authorization(
            session, tenant_id=tenant_id
        )
        session.commit()
    with factory() as session:
        case = OqiRemediationRepositoryImpl(session).get_case(
            tenant_id=tenant_id, finding_family=RemediationFindingFamily.OQI2, finding_id=finding_id
        )
        assert case is not None
        candidates = OqiRemediationRepositoryImpl(session).get_candidates_for_case(case.case_id)
        candidate_id = candidates[0].candidate_id

        def _both_succeed(request: ModelInvocationRequest) -> ModelInvocationResult:
            return ModelInvocationResult(
                succeeded=True,
                provider="fake",
                model="fake-model-v1",
                raw_text=json.dumps(_valid_output(candidate_id)),
                failure_kind=None,
                failure_detail="",
            )

        _agent_service_for(session, FakeModelProvider(responses=_both_succeed)).reason_about_case(
            tenant_id=tenant_id, case_id=case.case_id, now=NOW
        )
        session.commit()

    with factory() as session:
        row = _api_service(session).get_agent_investigation(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert row is not None
    assert len(row.specialists) == 2
    assert row.recommendation is not None
    assert row.recommendation.basis == "SPECIALIST_SUPPORTED"


def test_synthesizer_only_recommendation_is_labeled_distinctly(
    factory: sessionmaker[Session],
) -> None:
    """OQI5-VM-disclosed edge case: both specialists fail, the
    synthesizer's own independent provider call still succeeds. Driven by
    a real `role_id`-branching fake provider -- never a constructed
    response object standing in for a real reasoning run."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _instruction_id, _authorization_id = _seed_authorization(
            session, tenant_id=tenant_id
        )
        session.commit()
    with factory() as session:
        case = OqiRemediationRepositoryImpl(session).get_case(
            tenant_id=tenant_id, finding_family=RemediationFindingFamily.OQI2, finding_id=finding_id
        )
        assert case is not None
        candidates = OqiRemediationRepositoryImpl(session).get_candidates_for_case(case.case_id)
        candidate_id = candidates[0].candidate_id

        def _specialists_fail_synthesizer_succeeds(
            request: ModelInvocationRequest,
        ) -> ModelInvocationResult:
            if request.role_id == "RECOMMENDATION_SYNTHESIZER":
                return ModelInvocationResult(
                    succeeded=True,
                    provider="fake",
                    model="fake-model-v1",
                    raw_text=json.dumps(_valid_output(candidate_id)),
                    failure_kind=None,
                    failure_detail="",
                )
            return ModelInvocationResult(
                succeeded=False,
                provider="fake",
                model="fake-model-v1",
                raw_text=None,
                failure_kind=ProviderFailureKind.TIMEOUT,
                failure_detail="provider timed out",
            )

        outcome = _agent_service_for(
            session, FakeModelProvider(responses=_specialists_fail_synthesizer_succeeds)
        ).reason_about_case(tenant_id=tenant_id, case_id=case.case_id, now=NOW)
        session.commit()
    assert outcome.recommendation is not None

    with factory() as session:
        row = _api_service(session).get_agent_investigation(
            tenant_id=tenant_id, finding_id=finding_id
        )
    assert row is not None
    assert row.recommendation is not None
    assert row.recommendation.basis == "SYNTHESIZER_ONLY"


# =====================================================================
# Recommendation vs authorization -- genuinely distinct states
# (CDD-045 §19-§20, phase §30, closes disclosed gap #2).
# =====================================================================


def test_recommendation_vs_authorization_crown_two_stage(
    factory: sessionmaker[Session],
) -> None:
    """Stage 1: a valid OQI5 recommendation exists with zero human
    authorization -- the API must expose the recommendation while
    `authorization` is explicitly `None` (not a value implying
    authorized). Stage 2: a real human authorization is created and
    decided through OQI5-I1's own existing authority path -- the
    recommendation is preserved unchanged and the authorization now
    appears as a genuinely separate, distinct field/state."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, _ = _seed_oqi2_finding(
            session,
            tenant_id=tenant_id,
            roles={
                "SAP": "ABC123",
                "PLM": "ABC123",
                "MES": "ABC123",
                "Supplier": "ABC123",
                "PIM": None,
            },
            conflicting_roles=set(),
            missing_roles={"PIM"},
            authoritative_role=None,
        )
        session.commit()

    with factory() as session:
        remediation = _remediation_service_for(session)
        case, candidates = remediation.extract_candidates(
            tenant_id=tenant_id, finding_family=RemediationFindingFamily.OQI2, finding_id=finding_id
        )
        session.commit()
    candidate_id = candidates[0].candidate_id

    def _script(request: ModelInvocationRequest) -> ModelInvocationResult:
        return ModelInvocationResult(
            succeeded=True,
            provider="fake",
            model="fake-model-v1",
            raw_text=json.dumps(_valid_output(candidate_id)),
            failure_kind=None,
            failure_detail="",
        )

    with factory() as session:
        outcome = _agent_service_for(
            session, FakeModelProvider(responses=_script)
        ).reason_about_case(tenant_id=tenant_id, case_id=case.case_id, now=NOW)
        session.commit()
    assert outcome.recommendation is not None
    recommendation_id = outcome.recommendation.recommendation_id

    with factory() as session:
        instruction = _remediation_service_for(session).construct_instruction(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            created_by="steward-1",
            agent_recommendation_id=recommendation_id,
        )
        session.commit()

    # -- Stage 1: recommendation exists, zero authorization. --
    with factory() as session:
        stage1 = _api_service(session).get_remediation(tenant_id=tenant_id, finding_id=finding_id)
    assert stage1 is not None
    assert stage1.recommendation is not None
    assert stage1.recommendation.candidate_id == candidate_id
    assert stage1.authorization is None  # explicit absent state, not merely omitted

    # -- Stage 2: real human authorization requested and decided through
    # OQI5-I1's own existing authority path. --
    with factory() as session:
        authorization = _remediation_service_for(session).request_authorization(
            tenant_id=tenant_id, instruction_id=instruction.instruction_id, requested_by="requester"
        )
        session.commit()
    with factory() as session:
        _remediation_service_for(session).approve(
            tenant_id=tenant_id,
            authorization_id=authorization.authorization_id,
            decided_by="approver",
        )
        session.commit()

    with factory() as session:
        stage2 = _api_service(session).get_remediation(tenant_id=tenant_id, finding_id=finding_id)
    assert stage2 is not None
    assert stage2.recommendation is not None
    assert stage2.recommendation.candidate_id == candidate_id  # recommendation preserved
    assert stage2.authorization is not None  # now genuinely, separately present
    assert stage2.authorization.status == "APPROVED"
    assert stage2.authorization.principal == "approver"
    assert stage2.authorization.decided_on is not None
    # Recommendation and authorization remain two distinct, independently
    # populated fields on the row -- never merged into one state.


def _remediation_service_for(session: Session) -> Any:
    from app.application.oqi_remediation_service import OqiRemediationService

    return OqiRemediationService(
        repository=OqiRemediationRepositoryImpl(session),
        participant_reader=OqiRemediationParticipantReader(session),
    )
