import ast
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = REPOSITORY_ROOT / "backend" / "app" / "runtime"
AUTHORIZED_CHANGED_PATHS = {
    "README.md",
    "backend/app/runtime/__init__.py",
    "backend/app/runtime/contracts.py",
    "backend/app/runtime/engine.py",
    "backend/app/runtime/execution_state.py",
    "backend/app/runtime/execution_store.py",
    "backend/app/runtime/invocation.py",
    "backend/app/runtime/orchestration.py",
    "backend/app/tests/test_runtime_architecture.py",
    "backend/app/tests/test_runtime_contracts.py",
    "backend/app/tests/test_runtime_execution_state.py",
    "backend/app/tests/test_runtime_invocation.py",
    "backend/app/tests/test_runtime_orchestration.py",
    "backend/app/infrastructure/persistence/migrations/versions/0008_durable_execution.py",
    "backend/app/infrastructure/persistence/models/__init__.py",
    "backend/app/runtime/persistence/__init__.py",
    "backend/app/runtime/persistence/contracts.py",
    "backend/app/runtime/persistence/models.py",
    "backend/app/runtime/persistence/repository.py",
    "backend/app/runtime/recovery.py",
    "backend/app/tests/test_durable_execution_store.py",
    "backend/app/tests/test_execution_concurrency.py",
    "backend/app/tests/test_execution_persistence_architecture.py",
    "backend/app/tests/test_execution_persistence_contracts.py",
    "backend/app/tests/test_execution_persistence_integration.py",
    "backend/app/tests/test_execution_recovery.py",
    "backend/app/tests/test_execution_replay.py",
    "backend/app/tests/test_decision_engine.py",
    "backend/app/tests/test_governance_engine.py",
    "backend/app/tests/test_knowledge_engine.py",
    "backend/app/tests/test_persistence_integration.py",
}


def test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists() -> None:
    tracked = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    changed = set(tracked.stdout.splitlines()) | set(untracked.stdout.splitlines())
    assert changed <= AUTHORIZED_CHANGED_PATHS


def test_runtime_imports_only_standard_library_and_runtime_modules() -> None:
    forbidden_prefixes = (
        "app.api",
        "app.application",
        "app.core",
        "app.domain",
        "app.infrastructure",
        "fastapi",
        "sqlalchemy",
        "pydantic",
    )
    for path in RUNTIME_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        ]
        imports.extend(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        assert not any(
            module.startswith(forbidden_prefixes) for module in imports
        ), f"{path.name} bypasses the runtime boundary: {imports}"


def test_runtime_package_contains_only_authorized_top_level_files() -> None:
    assert {path.name for path in RUNTIME_ROOT.glob("*.py")} == {
        "__init__.py",
        "contracts.py",
        "engine.py",
        "execution_state.py",
        "execution_store.py",
        "invocation.py",
        "orchestration.py",
        "recovery.py",
    }
