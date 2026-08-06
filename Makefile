.PHONY: run test lint format typecheck migrate seed
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
	@echo "Unavailable in CDD-001: persistence migrations belong to a later assigned layer."
	@exit 2
seed:
	@echo "Unavailable in CDD-001: dataset loading and database seeding belong to a later assigned layer."
	@exit 2
