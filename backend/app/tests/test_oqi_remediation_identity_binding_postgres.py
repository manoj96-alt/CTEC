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

# isort: skip_file
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, String, Text, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command as alembic_command
from app.api.supplier_risk.audit import SecurityAuditService
from app.api.supplier_risk.authentication import (
    MAX_DISPLAY_NAME_LENGTH,
    TrustedPrincipal,
    normalize_display_name,
)
from app.api.supplier_risk.dependencies import container, principal
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.oqi_remediation.authorization import (
    RemediationAuthorization,
    RemediationAuthorizationStatus,
)
from app.domain.oqi_remediation.case import FindingFamily
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.api_security_audit_repository import (
    ApiSecurityAuditRepository,
)
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
)
from app.main import create_app
from app.tests.test_oidc_authentication import _token, _verifier
from app.tests.test_oqi_remediation_i1 import _seed_authorization, _seed_oqi2_finding, _service

NOW = datetime(2026, 1, 1, tzinfo=UTC)

_PRINCIPAL_A = "principal-a-requester"
_PRINCIPAL_B = "principal-b-approver"


def _principal(
    principal_id: str,
    *,
    tenant_id: str,
    display_name: str | None = None,
    scopes: tuple[str, ...] = ("oqi-remediation:authorize",),
) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
        display_name=display_name,
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


# =====================================================================
# CDD-091 §13/§21.3/§22.13 -- trusted human-readable display snapshots.
# Machine identity (`requested_by`/`decided_by`) remains the only security
# authority; the display snapshot is presentation evidence captured once per
# event from the same validated token, never from request input.
# =====================================================================

_FULL_SCOPES = ("oqi-remediation:prepare", "oqi-remediation:authorize", "oqi:read")
_PRINCIPAL_C = "principal-c-other"


def _actor(principal_id: str, *, tenant_id: str, display_name: str | None) -> TrustedPrincipal:
    return _principal(
        principal_id, tenant_id=tenant_id, display_name=display_name, scopes=_FULL_SCOPES
    )


def _seed_preparable_finding(session: Session, *, tenant_id: str) -> UUID:
    """A fresh OQI2 two-participant (SAP/PLM) conflict -- the Golden-shaped
    Finding whose real production `prepare` yields two PENDING candidates."""
    finding_id, _ = _seed_oqi2_finding(
        session,
        tenant_id=tenant_id,
        roles={"SAP": "OLD", "PLM": "NEW"},
        conflicting_roles={"SAP", "PLM"},
        missing_roles=set(),
        authoritative_role="PLM",
    )
    session.commit()
    return finding_id


def _prepare_via_router(
    migrated_engine: Engine, authenticated: TrustedPrincipal, finding_id: UUID, **body: object
) -> tuple[int, dict[str, Any]]:
    response = _client(migrated_engine, authenticated).post(
        f"/api/v1/oqi/findings/{finding_id}/remediation/prepare", json=body
    )
    return response.status_code, response.json()


def _prepared_authorization_ids(payload: dict[str, Any]) -> list[UUID]:
    authorizations = payload["authorizations"]
    assert isinstance(authorizations, list) and len(authorizations) == 2
    return [UUID(item["authorization_id"]) for item in authorizations]


def _decide_via_router(
    migrated_engine: Engine, authenticated: TrustedPrincipal, authorization_id: UUID, **body: object
) -> tuple[int, dict[str, Any]]:
    response = _client(migrated_engine, authenticated).post(
        f"/api/v1/oqi/remediation/authorizations/{authorization_id}/decide", json=body
    )
    return response.status_code, response.json()


def _read_authorizations_via_router(
    migrated_engine: Engine, authenticated: TrustedPrincipal, finding_id: UUID
) -> dict[str, dict[str, Any]]:
    response = _client(migrated_engine, authenticated).get(
        f"/api/v1/oqi/findings/{finding_id}/remediation"
    )
    assert response.status_code == 200
    return {
        candidate["authorization"]["authorization_id"]: candidate["authorization"]
        for candidate in response.json()["candidates"]
        if candidate["authorization"] is not None
    }


def _prepared(
    migrated_engine: Engine, *, tenant_id: str, requester_display: str | None
) -> tuple[UUID, UUID, UUID]:
    with sessionmaker(migrated_engine)() as session:
        finding_id = _seed_preparable_finding(session, tenant_id=tenant_id)
    status, payload = _prepare_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_A, tenant_id=tenant_id, display_name=requester_display),
        finding_id,
    )
    assert status == 202, payload
    first, second = _prepared_authorization_ids(payload)
    return finding_id, first, second


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        (123, None),
        (["Demo Approver"], None),
        ({"name": "Demo Approver"}, None),
        ("", None),
        ("   \t\n ", None),
        ("Demo Approver", "Demo Approver"),
        ("  Demo Approver \n", "Demo Approver"),
        ("Ana  María\tO’Neil-Ünal", "Ana  María\tO’Neil-Ünal"),
        ("x" * MAX_DISPLAY_NAME_LENGTH, "x" * MAX_DISPLAY_NAME_LENGTH),
        ("  " + "x" * MAX_DISPLAY_NAME_LENGTH + "  ", "x" * MAX_DISPLAY_NAME_LENGTH),
        ("x" * (MAX_DISPLAY_NAME_LENGTH + 1), None),
    ],
)
def test_display_claim_normalization_is_exactly_the_frozen_policy(
    raw: object, expected: str | None
) -> None:
    """CDD-091 §22.8: missing/non-string/empty/whitespace -> None; trim
    surrounding whitespace only (interior characters, case, and Unicode
    form preserved exactly); <=256 preserved; >256 -> None, never truncated."""
    assert normalize_display_name(raw) == expected


def test_real_signed_token_name_claim_becomes_display_name_never_principal() -> None:
    """The validated access token's `name` claim (and only it) populates
    `TrustedPrincipal.display_name`; `principal_id` stays the token's `sub`.
    An unusable `name` never fails authentication."""
    verifier, private = _verifier()
    named = verifier.verify(_token(private, sub="sub-approver", name="  Demo Approver "))
    assert named.principal_id == "sub-approver"
    assert named.display_name == "Demo Approver"
    for unusable in ({"name": "x" * 257}, {"name": "   "}, {"name": 42}):
        principal = verifier.verify(_token(private, sub="sub-approver", **unusable))
        assert principal.principal_id == "sub-approver"
        assert principal.display_name is None
    assert verifier.verify(_token(private, omit=("name",))).display_name is None


def test_domain_display_snapshot_invariant_is_defensive_only() -> None:
    """CDD-091 §22.9: a non-null snapshot must be non-blank and <=256; None is
    always valid. Production never reaches the error branch because the
    trust boundary already maps an overlong claim to None."""

    def build(**display: object) -> RemediationAuthorization:
        return RemediationAuthorization(
            authorization_id=uuid4(),
            tenant_id="tenant-x",
            instruction_id=uuid4(),
            payload_digest="0" * 64,
            requested_by=_PRINCIPAL_A,
            requested_on=NOW,
            status=RemediationAuthorizationStatus.PENDING,
            **display,  # type: ignore[arg-type]
        )

    assert build().requested_by_display_name is None
    assert build(requested_by_display_name="x" * 256).requested_by_display_name == "x" * 256
    for bad in ({"requested_by_display_name": "x" * 257}, {"decided_by_display_name": "  "}):
        with pytest.raises(ValidationException):
            build(**bad)


def test_requester_snapshot_travels_through_real_production_orchestration(
    migrated_engine: Engine,
) -> None:
    """§22.1/§22.4: token -> router -> ProductionRemediationOrchestrationService
    -> request_authorization -> domain -> repository -> ORM -> PostgreSQL ->
    read API. Both machine id and display snapshot persist and read back."""
    tenant_id = f"tenant-{uuid4()}"
    finding_id, first, second = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    with sessionmaker(migrated_engine)() as session:
        for authorization_id in (first, second):
            row = _authorization(session, authorization_id)
            assert row.requested_by == _PRINCIPAL_A
            assert row.requested_by_display_name == "Demo Steward"
            assert row.decided_by is None and row.decided_by_display_name is None

    read = _read_authorizations_via_router(
        migrated_engine, _actor(_PRINCIPAL_C, tenant_id=tenant_id, display_name=None), finding_id
    )
    assert read[str(first)]["requested_by"] == _PRINCIPAL_A
    assert read[str(first)]["requested_by_display_name"] == "Demo Steward"
    assert read[str(first)]["decided_by_display_name"] is None


def test_repeated_prepare_never_overwrites_requester_attribution(
    migrated_engine: Engine,
) -> None:
    """§22.5: the requester snapshot is written exactly once. A later,
    different caller repeating prepare never becomes the historical
    requester -- neither machine id nor display snapshot changes."""
    tenant_id = f"tenant-{uuid4()}"
    finding_id, first, second = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    status, payload = _prepare_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_C, tenant_id=tenant_id, display_name="Someone Else"),
        finding_id,
    )
    assert status == 202, payload
    assert sorted(_prepared_authorization_ids(payload)) == sorted([first, second])
    with sessionmaker(migrated_engine)() as session:
        for authorization_id in (first, second):
            row = _authorization(session, authorization_id)
            assert row.requested_by == _PRINCIPAL_A
            assert row.requested_by_display_name == "Demo Steward"


def test_approve_persists_decider_snapshot_and_sibling_supersession_fabricates_none(
    migrated_engine: Engine,
) -> None:
    """Approve: decider machine id + trusted display snapshot persist; the
    requester's snapshot is untouched; the sibling becomes SUPERSEDED (never
    REJECTED) with NO decider of either kind fabricated; the read API
    returns both snapshots."""
    tenant_id = f"tenant-{uuid4()}"
    finding_id, approved_id, sibling_id = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    status, payload = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name="Demo Approver"),
        approved_id,
        approve=True,
    )
    assert status == 200 and payload == {"case_status": "APPROVED"}

    with sessionmaker(migrated_engine)() as session:
        approved = _authorization(session, approved_id)
        assert approved.status == "APPROVED"
        assert approved.decided_by == _PRINCIPAL_B
        assert approved.decided_by_display_name == "Demo Approver"
        assert approved.decided_on is not None
        assert approved.requested_by == _PRINCIPAL_A
        assert approved.requested_by_display_name == "Demo Steward"
        sibling = _authorization(session, sibling_id)
        assert sibling.status == "SUPERSEDED"
        assert sibling.decided_by is None
        assert sibling.decided_by_display_name is None
        assert sibling.requested_by_display_name == "Demo Steward"

    read = _read_authorizations_via_router(
        migrated_engine, _actor(_PRINCIPAL_C, tenant_id=tenant_id, display_name=None), finding_id
    )
    assert read[str(approved_id)]["decided_by"] == _PRINCIPAL_B
    assert read[str(approved_id)]["decided_by_display_name"] == "Demo Approver"
    assert read[str(approved_id)]["requested_by_display_name"] == "Demo Steward"
    assert read[str(sibling_id)]["status"] == "SUPERSEDED"
    assert read[str(sibling_id)]["decided_by_display_name"] is None


def test_reject_persists_decider_snapshot(migrated_engine: Engine) -> None:
    tenant_id = f"tenant-{uuid4()}"
    _finding_id, rejected_id, _sibling_id = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    status, _ = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name="Demo Approver"),
        rejected_id,
        approve=False,
        rejection_reason="not this value",
    )
    assert status == 200
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, rejected_id)
        assert row.status == "REJECTED"
        assert row.decided_by == _PRINCIPAL_B
        assert row.decided_by_display_name == "Demo Approver"
        assert row.rejection_reason == "not this value"
        assert row.requested_by_display_name == "Demo Steward"


def test_same_display_name_distinct_principals_may_approve(migrated_engine: Engine) -> None:
    """§21.3 #1: display-name equality never implies principal equality."""
    tenant_id = f"tenant-{uuid4()}"
    _finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Alex Smith"
    )
    status, payload = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name="Alex Smith"),
        authorization_id,
        approve=True,
    )
    assert status == 200 and payload == {"case_status": "APPROVED"}
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.requested_by == _PRINCIPAL_A and row.decided_by == _PRINCIPAL_B
        assert row.requested_by_display_name == row.decided_by_display_name == "Alex Smith"


def test_same_principal_with_changed_display_name_is_still_self_approval_blocked(
    migrated_engine: Engine,
) -> None:
    """§21.3 #2: a rename can never bypass separation of duties -- the guard
    compares immutable machine identities only."""
    tenant_id = f"tenant-{uuid4()}"
    _finding_id, authorization_id, sibling_id = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Old Name"
    )
    status, payload = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_A, tenant_id=tenant_id, display_name="New Name"),
        authorization_id,
        approve=True,
    )
    assert status == 403
    assert payload["detail"]["code"] == "REMEDIATION_SELF_APPROVAL_PROHIBITED"
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.status == "PENDING"
        assert row.decided_by is None and row.decided_by_display_name is None
        assert row.requested_by_display_name == "Old Name"
        assert _authorization(session, sibling_id).status == "PENDING"


@pytest.mark.parametrize("claim", [None, 42, "", "   ", "x" * 257])
def test_missing_or_unusable_display_claim_never_blocks_governance(
    migrated_engine: Engine, claim: object
) -> None:
    """A missing/unusable `name` claim -- normalized at the trust boundary
    exactly as the real verifier does -- never blocks request or decision;
    the snapshot is simply NULL and the read API returns null."""
    display = normalize_display_name(claim)
    assert display is None
    tenant_id = f"tenant-{uuid4()}"
    finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display=display
    )
    status, _ = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name=display),
        authorization_id,
        approve=True,
    )
    assert status == 200
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.status == "APPROVED" and row.decided_by == _PRINCIPAL_B
        assert row.requested_by_display_name is None
        assert row.decided_by_display_name is None
    read = _read_authorizations_via_router(
        migrated_engine, _actor(_PRINCIPAL_C, tenant_id=tenant_id, display_name=None), finding_id
    )
    assert read[str(authorization_id)]["requested_by_display_name"] is None
    assert read[str(authorization_id)]["decided_by_display_name"] is None


def test_exactly_256_character_display_name_persists_exactly(migrated_engine: Engine) -> None:
    """§22.7: the full directory-bounded value round-trips through real
    VARCHAR(256) PostgreSQL storage unchanged (multibyte characters count as
    characters, not bytes)."""
    requester = "é" * MAX_DISPLAY_NAME_LENGTH
    decider = "D" * (MAX_DISPLAY_NAME_LENGTH - 1) + "Ω"
    assert normalize_display_name(requester) == requester
    tenant_id = f"tenant-{uuid4()}"
    finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display=requester
    )
    status, _ = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name=decider),
        authorization_id,
        approve=True,
    )
    assert status == 200
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.requested_by_display_name == requester
        assert row.decided_by_display_name == decider
    read = _read_authorizations_via_router(
        migrated_engine, _actor(_PRINCIPAL_C, tenant_id=tenant_id, display_name=None), finding_id
    )
    assert read[str(authorization_id)]["requested_by_display_name"] == requester
    assert read[str(authorization_id)]["decided_by_display_name"] == decider


def test_client_cannot_supply_any_actor_field_on_prepare(migrated_engine: Engine) -> None:
    """`PrepareRemediationRequest` is `extra="forbid"`: an injected actor
    field (machine or display) is rejected with 422 and creates nothing."""
    tenant_id = f"tenant-{uuid4()}"
    with sessionmaker(migrated_engine)() as session:
        finding_id = _seed_preparable_finding(session, tenant_id=tenant_id)
    for spoof in (
        {"requested_by": "spoofed-principal"},
        {"requested_by_display_name": "CEO"},
    ):
        status, _ = _prepare_via_router(
            migrated_engine,
            _actor(_PRINCIPAL_A, tenant_id=tenant_id, display_name="Demo Steward"),
            finding_id,
            **spoof,
        )
        assert status == 422
    with sessionmaker(migrated_engine)() as session:
        assert (
            session.execute(
                select(OqiRemediationAuthorizationORM).where(
                    OqiRemediationAuthorizationORM.tenant_id == tenant_id
                )
            ).first()
            is None
        )


def test_client_supplied_actor_fields_on_decide_have_zero_effect(
    migrated_engine: Engine,
) -> None:
    """`DecideAuthorizationRequest` ignores unknown fields; every spoofed
    actor value (machine and display, for both requester and decider) must
    have zero effect on persisted attribution."""
    tenant_id = f"tenant-{uuid4()}"
    _finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    status, _ = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name="Demo Approver"),
        authorization_id,
        approve=True,
        decided_by="spoofed-principal",
        decided_by_display_name="Spoofed CEO",
        requested_by="spoofed-requester",
        requested_by_display_name="Spoofed Requester",
    )
    assert status == 200
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.decided_by == _PRINCIPAL_B
        assert row.decided_by_display_name == "Demo Approver"
        assert row.requested_by == _PRINCIPAL_A
        assert row.requested_by_display_name == "Demo Steward"


def test_historical_snapshot_is_never_rewritten_by_later_identity(
    migrated_engine: Engine,
) -> None:
    """§7/§11: the snapshot is stored event evidence, not a live lookup. The
    same principals later presenting different names (a simulated directory
    rename) -- reading, and repeating prepare -- never rewrite history."""
    tenant_id = f"tenant-{uuid4()}"
    finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name="Demo Approver"),
        authorization_id,
        approve=True,
    )
    renamed_steward = _actor(_PRINCIPAL_A, tenant_id=tenant_id, display_name="Renamed Steward")
    renamed_approver = _actor(_PRINCIPAL_B, tenant_id=tenant_id, display_name="Renamed Approver")
    status, _ = _prepare_via_router(migrated_engine, renamed_steward, finding_id)
    assert status == 202
    read = _read_authorizations_via_router(migrated_engine, renamed_approver, finding_id)
    assert read[str(authorization_id)]["requested_by_display_name"] == "Demo Steward"
    assert read[str(authorization_id)]["decided_by_display_name"] == "Demo Approver"


def test_cross_tenant_decider_cannot_decide_or_stamp_a_snapshot(
    migrated_engine: Engine,
) -> None:
    tenant_id, other_tenant = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    _finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    status, _ = _decide_via_router(
        migrated_engine,
        _actor(_PRINCIPAL_B, tenant_id=other_tenant, display_name="Foreign Approver"),
        authorization_id,
        approve=True,
    )
    assert status != 200
    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.status == "PENDING"
        assert row.decided_by is None and row.decided_by_display_name is None


def _alembic_config(migrated_engine: Engine) -> Config:
    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url", migrated_engine.url.render_as_string(hide_password=False)
    )
    return config


def _alembic_version(migrated_engine: Engine) -> str:
    with migrated_engine.connect() as connection:
        return connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()


def test_migration_head_columns_and_version_row(migrated_engine: Engine) -> None:
    """§22.6/§22.7: the real `alembic_version` row stores the 31-character
    revision id, and both snapshot columns are nullable VARCHAR(256)."""
    assert _alembic_version(migrated_engine) == "0049_oqi_remediation_actor_name"
    columns = {
        column["name"]: column
        for column in inspect(migrated_engine).get_columns("oqi_remediation_authorizations")
    }
    for name in ("requested_by_display_name", "decided_by_display_name"):
        assert columns[name]["nullable"] is True
        column_type = columns[name]["type"]
        assert isinstance(column_type, String) and not isinstance(column_type, Text)
        assert column_type.length == MAX_DISPLAY_NAME_LENGTH


def test_migration_downgrade_upgrade_round_trip_keeps_existing_rows_readable(
    migrated_engine: Engine,
) -> None:
    """Downgrade 0049 -> 0048 drops exactly the two snapshot columns while
    pre-existing rows survive; upgrading back (the real upgrade-from-0048
    path) leaves those historical rows readable with NULL snapshots -- no
    backfill, no fabricated identity -- through the real read API."""
    tenant_id = f"tenant-{uuid4()}"
    finding_id, authorization_id, _ = _prepared(
        migrated_engine, tenant_id=tenant_id, requester_display="Demo Steward"
    )
    config = _alembic_config(migrated_engine)
    alembic_command.downgrade(config, "0048_oqi_remediation_mutex")
    try:
        assert _alembic_version(migrated_engine) == "0048_oqi_remediation_mutex"
        names = {
            column["name"]
            for column in inspect(migrated_engine).get_columns("oqi_remediation_authorizations")
        }
        assert "requested_by_display_name" not in names
        assert "decided_by_display_name" not in names
    finally:
        alembic_command.upgrade(config, "head")
    assert _alembic_version(migrated_engine) == "0049_oqi_remediation_actor_name"

    with sessionmaker(migrated_engine)() as session:
        row = _authorization(session, authorization_id)
        assert row.requested_by == _PRINCIPAL_A
        assert row.requested_by_display_name is None
        assert row.decided_by_display_name is None
    read = _read_authorizations_via_router(
        migrated_engine, _actor(_PRINCIPAL_C, tenant_id=tenant_id, display_name=None), finding_id
    )
    assert read[str(authorization_id)]["requested_by"] == _PRINCIPAL_A
    assert read[str(authorization_id)]["requested_by_display_name"] is None
