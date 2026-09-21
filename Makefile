.PHONY: run test lint format typecheck migrate seed reset-db verify-architecture demo-reset demo-verify
run:
	docker compose up --build
test:
	cd backend && pytest
	cd frontend && npm test -- --run --coverage
lint:
	cd backend && ruff check . && black --check . && isort --check-only .
	cd frontend && npm run lint && npm run format:check
format:
	cd backend && black . && isort . && ruff check --fix .
	cd frontend && npm run format
typecheck:
	cd backend && mypy app
	cd frontend && npm run typecheck
migrate:
	cd backend && alembic -c alembic.ini upgrade head
seed:
	cd backend && python -m app.infrastructure.persistence.database_cli seed ../datasets/edt-001/v3/CTEC_YC_SupplyChain_Dataset_v3.zip
reset-db:
	cd backend && python -m app.infrastructure.persistence.database_cli reset-db
demo-reset:
	cd backend && python -m app.infrastructure.persistence.database_cli demo-reset
demo-verify:
	cd backend && python -m app.infrastructure.persistence.database_cli demo-verify
verify-architecture:
	python3 scripts/verify_architecture_release.py
