from typing import cast

from sqlalchemy import Table

from app.runtime.persistence.models import RuntimeExecutionORM


def test_idempotency_and_optimistic_concurrency_constraints_exist() -> None:
    table = cast(Table, RuntimeExecutionORM.__table__)
    unique = {
        tuple(column.name for column in item.columns)
        for item in table.constraints
        if hasattr(item, "columns")
    }
    assert ("tenant_id", "protocol_version", "request_id") in unique
    assert "revision" in table.columns
