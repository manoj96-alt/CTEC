.PHONY: run test lint format typecheck migrate seed reset-db
run:
	docker compose up --build
test:
	cd cognitive-engine/backend && python -m pytest
	cd cognitive-engine/frontend && npm test -- --run --coverage
lint:
	cd cognitive-engine/backend && python -m ruff check . && python -m black --check . && python -m isort --check-only .
	cd cognitive-engine/frontend && npm run lint && npm run format:check
format:
	cd cognitive-engine/backend && python -m black . && python -m isort . && python -m ruff check --fix .
	cd cognitive-engine/frontend && npm run format
typecheck:
	cd cognitive-engine/backend && python -m mypy app
	cd cognitive-engine/frontend && npm run typecheck
migrate:
	cd cognitive-engine/backend && alembic -c alembic.ini upgrade head
seed:
	cd cognitive-engine/backend && python -m app.infrastructure.persistence.database_cli seed ../../sample-data/edt-001/v3/CTEC_YC_SupplyChain_Dataset_v3.zip
reset-db:
	cd cognitive-engine/backend && python -m app.infrastructure.persistence.database_cli reset-db
