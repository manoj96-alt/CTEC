# isort: skip_file
import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

import alembic.command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.infrastructure.persistence.database import create_database_engine
from app.infrastructure.persistence.seed_loader import SeedLoader
from app.infrastructure.persistence.session import create_session_factory


def _alembic_config() -> Config:
    backend_root = Path(__file__).parents[3]
    return Config(backend_root / "alembic.ini")


def migrate() -> None:
    alembic.command.upgrade(_alembic_config(), "head")


def reset_database() -> None:
    config = _alembic_config()
    alembic.command.downgrade(config, "base")
    alembic.command.upgrade(config, "head")


def seed(archive: Path) -> None:
    settings = get_settings()
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        loader = SeedLoader(session)
        summary = loader.load(archive)
        counts = loader.verify_counts(archive)
    print(json.dumps({**asdict(summary), **counts}, default=str, sort_keys=True))


# CDD-085 §18/§20 (Demo Readiness): demo-reset performs a full schema
# downgrade/upgrade before re-seeding -- the ONLY way to clear a prior
# demo session's own real, durably-committed remediation
# authorization/execution-report state (DemoOqiSeeder itself is
# idempotent, but never touches those tables, so a bare re-seed alone
# would leave that contamination in place). Because this discards
# everything in the target database, it must fail closed: both an
# explicit opt-in environment variable AND a database-host allowlist
# check must pass, or the command makes zero database change.
_DEMO_RESET_ALLOWED_HOSTS = frozenset({"localhost", "127.0.0.1", "postgres"})


class DemoResetNotAllowedError(Exception):
    """Raised when demo-reset's fail-closed guard rejects the target
    environment. Never caught internally -- always propagates to a
    non-zero exit with a clear, specific reason."""


def _assert_demo_reset_allowed(database_url: str) -> None:
    if os.environ.get("CTEC_DEMO_RESET_ALLOWED") != "true":
        raise DemoResetNotAllowedError(
            "demo-reset refused: CTEC_DEMO_RESET_ALLOWED is not set to exactly 'true'. "
            "This command destroys and rebuilds the entire target schema; it must never run "
            "without an explicit, deliberate opt-in."
        )
    host = make_url(database_url).host
    if host not in _DEMO_RESET_ALLOWED_HOSTS:
        raise DemoResetNotAllowedError(
            f"demo-reset refused: database host {host!r} is not in the allowed local/demo host "
            f"list {sorted(_DEMO_RESET_ALLOWED_HOSTS)!r}. This command must never run against a "
            "database it cannot independently confirm is local/demo-only."
        )


def demo_reset() -> None:
    """CDD-085 §18: fail-closed guard, then the existing, unmodified
    reset_database() (downgrade base -> upgrade head), then the existing,
    unmodified OntologySeeder/BlueprintSeeder calls (the same two the
    Docker entrypoint already makes), then the (Golden-Story-updated)
    DemoOqiSeeder. Never the EDT-001 SeedLoader -- that remains the
    separate, unrelated `seed` command above."""
    settings = get_settings()
    assert settings.database_url is not None, "CTEC_DATABASE_URL must be set to run demo-reset"
    _assert_demo_reset_allowed(settings.database_url)

    reset_database()

    from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder
    from app.infrastructure.persistence.demo_oqi_seeder import DemoOqiSeeder
    from app.infrastructure.persistence.ontology_seed import OntologySeeder

    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        BlueprintSeeder(session).load()
        session.commit()
        summary = DemoOqiSeeder(session).seed()
        session.commit()
    print(json.dumps(asdict(summary), default=str, sort_keys=True))


def demo_verify() -> bool:
    """CDD-085 §19: read-only. Asserts the exact deterministic Golden
    Demo state contract, printing a specific PASS/FAIL line for each
    assertion and returning True only if every one passed. Makes zero
    database change."""
    from app.infrastructure.persistence.demo_oqi_seeder import (
        _AURORA_BOM_ID,
        _AURORA_MATERIAL_ID,
        _H6_PRODUCT_A_ID,
        _H6_PRODUCT_B_ID,
        _H6_PRODUCT_C_ID,
        _PLM_FIELD_ID,
        _SAP_FIELD_ID,
        _SUPPLIER_ENTITY_ID,
    )
    from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
    from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
    from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
    from app.infrastructure.persistence.models.oqi_cross_source_finding import (
        QualityComparisonFindingORM,
    )
    from app.infrastructure.persistence.models.oqi_uniqueness import (
        UniquenessAdjudicationORM,
        UniquenessFindingORM,
    )
    from app.infrastructure.persistence.oqi_business_impact_repository import (
        OqiBusinessImpactRepositoryImpl,
    )
    from app.domain.oqi_ontology_impact.evaluation import OntologyElementType

    settings = get_settings()
    assert settings.database_url is not None, "CTEC_DATABASE_URL must be set to run demo-verify"
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    tenant_id = BOOTSTRAP_DEMO_TENANT_ID

    results: list[tuple[str, bool, str]] = []

    def _check(name: str, condition: bool, detail: str) -> None:
        results.append((name, condition, detail))

    with factory() as session:
        supplier = session.get(EnterpriseEntity, _SUPPLIER_ENTITY_ID)
        _check(
            "golden_supplier_exists",
            supplier is not None and supplier.enterprise_entity_name == "Meridian Cell Components",
            f"name={supplier.enterprise_entity_name if supplier else None!r}",
        )

        sap_evidence = session.scalar(
            select(FieldValueEvidenceORM).where(
                FieldValueEvidenceORM.source_field_id == _SAP_FIELD_ID
            )
        )
        plm_evidence = session.scalar(
            select(FieldValueEvidenceORM).where(
                FieldValueEvidenceORM.source_field_id == _PLM_FIELD_ID
            )
        )
        _check(
            "sap_evidence_us",
            sap_evidence is not None and sap_evidence.observed_representation == "US",
            f"value={sap_evidence.observed_representation if sap_evidence else None!r}",
        )
        _check(
            "plm_evidence_mx",
            plm_evidence is not None and plm_evidence.observed_representation == "MX",
            f"value={plm_evidence.observed_representation if plm_evidence else None!r}",
        )

        consistency_finding = session.scalar(
            select(QualityComparisonFindingORM).where(
                QualityComparisonFindingORM.tenant_id == tenant_id,
                QualityComparisonFindingORM.quality_condition_id
                == "oqi-demo-supplier-country-of-origin",
            )
        )
        _check(
            "oqi2_finding_open",
            consistency_finding is not None and consistency_finding.status == "OPEN",
            f"status={consistency_finding.status if consistency_finding else None!r}",
        )

        bi_repo = OqiBusinessImpactRepositoryImpl(session)
        state = bi_repo.compute_subject_finding_state(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=_SUPPLIER_ENTITY_ID,
        )
        _check(
            "supplier_has_open_finding_refs",
            len(state.open_finding_refs) > 0,
            f"count={len(state.open_finding_refs)}",
        )

        aurora_product = session.get(EnterpriseEntity, _H6_PRODUCT_A_ID)
        aurora_material = session.get(EnterpriseEntity, _AURORA_MATERIAL_ID)
        aurora_bom = session.get(EnterpriseEntity, _AURORA_BOM_ID)
        _check(
            "aurora_x1_product_exists",
            aurora_product is not None and aurora_product.enterprise_entity_name == "Aurora X1",
            f"name={aurora_product.enterprise_entity_name if aurora_product else None!r}",
        )
        _check("aurora_material_exists", aurora_material is not None, "")
        _check("aurora_bom_exists", aurora_bom is not None, "")

        h6_finding = session.scalar(
            select(UniquenessFindingORM).where(
                UniquenessFindingORM.tenant_id == tenant_id,
                UniquenessFindingORM.member_a_id.in_((_H6_PRODUCT_A_ID, _H6_PRODUCT_B_ID)),
                UniquenessFindingORM.member_b_id.in_((_H6_PRODUCT_A_ID, _H6_PRODUCT_B_ID)),
            )
        )
        _check(
            "h6_aurora_pair_open_candidate",
            h6_finding is not None and h6_finding.status == "OPEN",
            f"status={h6_finding.status if h6_finding else None!r}",
        )
        stale_adjudication = (
            session.scalar(
                select(UniquenessAdjudicationORM).where(
                    UniquenessAdjudicationORM.tenant_id == tenant_id,
                    UniquenessAdjudicationORM.candidate_id == h6_finding.candidate_id,
                )
            )
            if h6_finding is not None
            else None
        )
        _check(
            "h6_pair_no_prior_adjudication",
            stale_adjudication is None,
            "a stale adjudication exists" if stale_adjudication is not None else "",
        )

        distinct_control = session.get(EnterpriseEntity, _H6_PRODUCT_C_ID)
        _check(
            "nimbus_control_exists",
            distinct_control is not None
            and distinct_control.enterprise_entity_name == "Nimbus S2 Controller",
            f"name={distinct_control.enterprise_entity_name if distinct_control else None!r}",
        )

    all_passed = True
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {name}" + (f" -- {detail}" if detail else ""))
        all_passed = all_passed and passed

    print("demo-verify: " + ("ALL CHECKS PASSED" if all_passed else "CHECKS FAILED"))
    return all_passed


def main() -> None:
    parser = argparse.ArgumentParser(description="CTEC persistence administration")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("migrate")
    subcommands.add_parser("reset-db")
    seed_parser = subcommands.add_parser("seed")
    seed_parser.add_argument("archive", type=Path)
    subcommands.add_parser("demo-reset")
    subcommands.add_parser("demo-verify")
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    elif args.command == "reset-db":
        reset_database()
    elif args.command == "demo-reset":
        try:
            demo_reset()
        except DemoResetNotAllowedError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(1)
    elif args.command == "demo-verify":
        if not demo_verify():
            sys.exit(1)
    else:
        seed(args.archive)


if __name__ == "__main__":
    main()
