"""NOETVA-GOVERNED-AUTHORITY-BINDING-I-R1 -- real HTTP/router proof that the
decide-authorization decision-actor identity is bound exclusively to the
server-validated authenticated principal, never to client-supplied input.

AZURE-GOLDEN-DEMO-PARITY-VM-R2 adversarially proved a real defect: the live
`decide_authorization` endpoint read `decided_by` from the request body
instead of `authenticated.principal_id`. The existing unit test
(`test_self_approval_is_rejected` in `test_oqi_remediation_i1.py`) only
ever exercised `OqiRemediationService.approve()` directly with hand-picked
string literals -- it could never have caught this, because the defect
lived one layer up, in how the HTTP router populated that argument from a
real authenticated principal versus a real request body. This file closes
exactly that gap: real FastAPI router, real `OqiProductExperienceService`/
`OqiRemediationService`, real disposable PostgreSQL, two distinct real
`TrustedPrincipal`s standing in for two distinct real Entra subjects --
mirroring the established full-stack pattern in
`test_ontology_copilot_full_stack_postgres.py`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.oqi_remediation.case import FindingFamily
from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditRepository,
)
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
)
from app.main import create_app
from app.tests.test_oqi_remediation_i1 import _seed_authorization, _seed_oqi2_finding, _service

NOW = datetime(2026, 1, 1, tzinfo=UTC)

_PRINCIPAL_A = "principal-a-requester"
_PRINCIPAL_B = "principal-b-approver"


def _principal(principal_id: str, *, tenant_id: str) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        scopes=("oqi-remediation:authorize",),
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _client(migrated_engine: Engine, authenticated: TrustedPrincipal) -> TestClient:
    sessions = sessionmaker(migrated_engine)
    app = create_app()
    app.dependency_overrides[principal] = lambda: authenticated
    app.dependency_overrides[container] = lambda: Container(
        Settings(),
        ontology_sessions=sessions,
        security_audit=SecurityAuditService(ApiSecurityAuditRepository(sessions)),
    )
    return TestClient(app)


def _authorization(session: Session, authorization_id: UUID) -> OqiRemediationAuthorizationORM:
    row = session.get(OqiRemediationAuthorizationORM, authorization_id)
    assert row is not None
    return row


def _seed_two_candidate_authorizations(
    session: Session, *, tenant_id: str, requested_by: str
) -> tuple[UUID, UUID, UUID]:
    """Like `_seed_authorization`, but requests authorization for BOTH
    candidates of the fresh OQI2 2-participant conflict (US/MX-shaped),
    matching the real production flow (CDD-087 Golden) where both
    candidates are simultaneously PENDING before any decision -- required
    to genuinely exercise the APPROVED/SUPERSEDED sibling invariant."""
    finding_id, _ = _seed_oqi2_finding(
        session,
        tenant_id=tenant_id,
        roles={"SAP": "OLD", "PLM": "NEW"},
        conflicting_roles={"SAP", "PLM"},
        missing_roles=set(),
        authoritative_role="PLM",
    )
    session.commit()
    service = _service(session)
    _, candidates = service.extract_candidates(
        tenant_id=tenant_id, finding_family=FindingFamily.OQI2, finding_id=finding_id
    )
    session.commit()
    authorization_ids = []
    for candidate in candidates:
        instruction = service.construct_instruction(
            tenant_id=tenant_id, candidate_id=candidate.candidate_id, created_by="system"
        )
        session.commit()
        authorization = service.request_authorization(
            tenant_id=tenant_id,
            instruction_id=instruction.instruction_id,
            requested_by=requested_by,
        )
        session.commit()
        authorization_ids.append(authorization.authorization_id)
    return finding_id, authorization_ids[0], authorization_ids[1]


def test_same_principal_decide_fails_closed_through_real_http_router(
    migrated_engine: Engine,
) -> None:
    """Principal A requests; Principal A then calls the real HTTP decide
    endpoint. Must fail with REMEDIATION_SELF_APPROVAL_PROHIBITED -- the
    exact live defect AZURE-GOLDEN-DEMO-PARITY-VM-R2 found, where the two
    sides of this comparison came from different, client-controllable
    sources instead of both being the same server-authoritative
    `authenticated.principal_id`."""
    tenant_id = f"tenant-{uuid4()}"
    sessions = sessionmaker(migrated_engine)
    with sessions() as session:
        _finding_id, authorization_id, sibling_id = _seed_two_candidate_authorizations(
            session, tenant_id=tenant_id, requested_by=_PRINCIPAL_A
        )

    client = _client(migrated_engine, _principal(_PRINCIPAL_A, tenant_id=tenant_id))
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{authorization_id}/decide",
        json={"approve": True},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "REMEDIATION_SELF_APPROVAL_PROHIBITED"

    with sessions() as session:
        target = _authorization(session, authorization_id)
        assert target.status == "PENDING"
        assert target.decided_by is None
        # No candidate becomes APPROVED, no sibling becomes SUPERSEDED, as a
        # result of a self-approval attempt (VM-R2 §7).
        sibling = _authorization(session, sibling_id)
        assert sibling.status == "PENDING"


def test_distinct_principal_decide_succeeds_and_persists_server_identity(
    migrated_engine: Engine,
) -> None:
    """Principal A requests; Principal B calls the real HTTP decide
    endpoint. Must succeed, with exactly one candidate APPROVED and its
    sibling SUPERSEDED (never REJECTED), and the persisted actor must be
    Principal B's own authenticated id -- never anything the client's
    request body could have supplied."""
    tenant_id = f"tenant-{uuid4()}"
    sessions = sessionmaker(migrated_engine)
    with sessions() as session:
        _finding_id, authorization_id, sibling_id = _seed_two_candidate_authorizations(
            session, tenant_id=tenant_id, requested_by=_PRINCIPAL_A
        )

    client = _client(migrated_engine, _principal(_PRINCIPAL_B, tenant_id=tenant_id))
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{authorization_id}/decide",
        json={"approve": True},
    )
    assert response.status_code == 200
    assert response.json() == {"case_status": "APPROVED"}

    with sessions() as session:
        target = _authorization(session, authorization_id)
        assert target.status == "APPROVED"
        assert target.decided_by == _PRINCIPAL_B

        sibling = _authorization(session, sibling_id)
        assert sibling.status == "SUPERSEDED"
        assert sibling.status != "REJECTED"


def test_spoofed_decided_by_in_request_body_cannot_control_persisted_actor(
    migrated_engine: Engine,
) -> None:
    """Mandatory per VM-R2 §9: a malicious/buggy client sending a
    `decided_by` field in the request body (whether or not the schema still
    accepts it as an unknown/ignored key) must never be able to make that
    value the persisted decision actor. The persisted actor must always be
    Principal B's own server-validated identity."""
    tenant_id = f"tenant-{uuid4()}"
    sessions = sessionmaker(migrated_engine)
    with sessions() as session:
        _finding_id, _instruction_id, authorization_id = _seed_authorization(
            session, tenant_id=tenant_id, requested_by=_PRINCIPAL_A
        )
        session.commit()

    client = _client(migrated_engine, _principal(_PRINCIPAL_B, tenant_id=tenant_id))
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{authorization_id}/decide",
        json={"approve": True, "decided_by": "spoofed-principal"},
    )
    assert response.status_code == 200

    with sessions() as session:
        target = _authorization(session, authorization_id)
        assert target.decided_by == _PRINCIPAL_B
        assert target.decided_by != "spoofed-principal"


def test_reject_path_also_binds_actor_to_authenticated_principal(
    migrated_engine: Engine,
) -> None:
    """VM-R2 §10: the same server-authoritative identity binding applies to
    REJECT, not only APPROVE -- including when the client attempts to
    supply a spoofed actor alongside the rejection."""
    tenant_id = f"tenant-{uuid4()}"
    sessions = sessionmaker(migrated_engine)
    with sessions() as session:
        _finding_id, _instruction_id, authorization_id = _seed_authorization(
            session, tenant_id=tenant_id, requested_by=_PRINCIPAL_A
        )
        session.commit()

    client = _client(migrated_engine, _principal(_PRINCIPAL_B, tenant_id=tenant_id))
    response = client.post(
        f"/api/v1/oqi/remediation/authorizations/{authorization_id}/decide",
        json={
            "approve": False,
            "decided_by": "spoofed-principal",
            "rejection_reason": "wrong field",
        },
    )
    assert response.status_code == 200

    with sessions() as session:
        target = _authorization(session, authorization_id)
        assert target.status == "REJECTED"
        assert target.decided_by == _PRINCIPAL_B
        assert target.decided_by != "spoofed-principal"
