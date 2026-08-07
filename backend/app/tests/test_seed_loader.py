from pathlib import Path

from sqlalchemy import Engine, select

from app.core.bootstrap import SEED_VERSION
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.seed_loader import SeedLoader
from app.infrastructure.persistence.session import create_session_factory

DATASET = Path("../datasets/edt-001/v3/CTEC_YC_SupplyChain_Dataset_v3.zip")


def test_seed_loader_is_idempotent_and_preserves_candidate_assertions(
    migrated_engine: Engine,
) -> None:
    factory = create_session_factory(migrated_engine)
    with factory.begin() as session:
        loader = SeedLoader(session)
        first = loader.load(DATASET)
        first_counts = loader.verify_counts(DATASET)
    with factory.begin() as session:
        loader = SeedLoader(session)
        second = loader.load(DATASET)
        second_counts = loader.verify_counts(DATASET)
        candidate_objects = session.scalars(
            select(SourceObject).where(
                SourceObject.source_object_name.like(f"{SEED_VERSION}:Assertions.csv:%")
            )
        ).all()
        assertion_count = session.query(Assertion).count()

    assert first.csv_files == 19
    assert first.source_systems_created == 6
    assert first.source_objects_created == first_counts["expected_source_objects"]
    assert first_counts == second_counts
    assert second.source_systems_created == 0
    assert second.source_objects_created == 0
    assert len(candidate_objects) == 3
    assert assertion_count == 0
