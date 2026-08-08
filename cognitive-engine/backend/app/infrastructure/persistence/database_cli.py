# isort: skip_file
import argparse
import json
from dataclasses import asdict
from pathlib import Path

import alembic.command
from alembic.config import Config

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


def main() -> None:
    parser = argparse.ArgumentParser(description="CTEC persistence administration")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("migrate")
    subcommands.add_parser("reset-db")
    seed_parser = subcommands.add_parser("seed")
    seed_parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    if args.command == "migrate":
        migrate()
    elif args.command == "reset-db":
        reset_database()
    else:
        seed(args.archive)


if __name__ == "__main__":
    main()
