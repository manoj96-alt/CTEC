#!/bin/sh
# Runs database migrations and idempotent ontology/Blueprint seeding before
# starting the server. Never destroys or resets existing data: `alembic
# upgrade head` only ever moves forward, and both OntologySeeder and
# BlueprintSeeder check for existing rows before creating anything (see
# app/infrastructure/persistence/ontology_seed.py and
# app/infrastructure/persistence/blueprint_seed.py). The Blueprint seed runs
# only after the ontology seed has committed, since it resolves its
# EntityType/RelationshipType references by name against that already-
# governed vocabulary.
set -e

echo "[entrypoint] running database migrations..."
python -m alembic upgrade head

echo "[entrypoint] seeding ontology (idempotent)..."
python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.infrastructure.persistence.ontology_seed import OntologySeeder

settings = get_settings()
engine = create_engine(settings.database_url)
factory = sessionmaker(engine)
with factory() as session:
    summary = OntologySeeder(session).load()
    session.commit()
print(f'[entrypoint] ontology seed: {summary}')
"

echo "[entrypoint] seeding canonical Blueprint (idempotent)..."
python -c "
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings
from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder

settings = get_settings()
engine = create_engine(settings.database_url)
factory = sessionmaker(engine)
with factory() as session:
    summary = BlueprintSeeder(session).load()
    session.commit()
print(f'[entrypoint] blueprint seed: {summary}')
"

echo "[entrypoint] starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
