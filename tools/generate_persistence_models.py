"""Generate SQLAlchemy models from the frozen ECOM Physical Model v1.3 DDL."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def class_name(table: str) -> str:
    irregular = {
        "enterprises": "Enterprise",
        "enterprise_types": "EnterpriseType",
        "countries": "Country",
        "business_domains": "BusinessDomain",
        "institutional_concepts": "InstitutionalConcept",
        "relationship_types": "RelationshipType",
        "entity_types": "EntityType",
        "enterprise_entities": "EnterpriseEntity",
        "evidences": "Evidence",
        "assertions": "Assertion",
        "institutional_relationships": "InstitutionalRelationship",
        "knowledges": "Knowledge",
        "reasons": "Reason",
        "reason_graphs": "ReasonGraph",
        "decision_objectives": "DecisionObjective",
        "occasions": "Occasion",
        "pattern_of_relevances": "PatternOfRelevance",
        "decisions": "Decision",
        "decision_states": "DecisionState",
        "institutional_actions": "InstitutionalAction",
        "outcomes": "Outcome",
        "experiences": "Experience",
        "governances": "Governance",
        "accountable_owners": "AccountableOwner",
        "source_systems": "SourceSystem",
        "source_objects": "SourceObject",
        "institutional_acts": "InstitutionalAct",
        "contexts": "Context",
    }
    return irregular.get(table, "".join(part.title() for part in table.split("_")))


def module_name(table: str) -> str:
    return table[:-3] + "y" if table.endswith("ies") else table.removesuffix("s")


def parse_enums(sql: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name, values in re.findall(r"CREATE TYPE (\w+) AS ENUM \((.*?)\);", sql):
        result[name] = re.findall(r"'([^']+)'", values)
    return result


def generate(sql_path: Path, output_dir: Path) -> None:
    sql = sql_path.read_text()
    enums = parse_enums(sql)
    foreign_keys: dict[tuple[str, str], tuple[str, str]] = {}
    for table, constraint, column, target_table, target_column in re.findall(
        r"ALTER TABLE (\w+) ADD CONSTRAINT (\w+) FOREIGN KEY \((\w+)\) "
        r"REFERENCES (\w+)\((\w+)\);",
        sql,
    ):
        foreign_keys[(table, column)] = (constraint, f"{target_table}.{target_column}")

    unique_constraints: dict[str, list[tuple[str, list[str]]]] = {}
    for table, constraint, columns in re.findall(
        r"ALTER TABLE (\w+) ADD CONSTRAINT (\w+) UNIQUE \(([^)]+)\);", sql
    ):
        unique_constraints.setdefault(table, []).append(
            (constraint, [column.strip() for column in columns.split(",")])
        )

    checks: dict[str, list[tuple[str, str]]] = {}
    for table, constraint, expression in re.findall(
        r"ALTER TABLE (\w+) ADD CONSTRAINT (\w+) CHECK \((.*?)\);", sql, re.DOTALL
    ):
        checks.setdefault(table, []).append((constraint, " ".join(expression.split())))

    indexes: dict[str, list[tuple[str, list[str]]]] = {}
    for name, table, columns in re.findall(r"CREATE INDEX (\w+) ON (\w+)\(([^)]+)\);", sql):
        indexes.setdefault(table, []).append(
            (name, [column.strip() for column in columns.split(",")])
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    modules: list[tuple[str, str]] = []
    table_pattern = re.compile(r"CREATE TABLE (\w+) \((.*?)\n\);", re.DOTALL)
    for table, body in table_pattern.findall(sql):
        cls = class_name(table)
        module = module_name(table)
        modules.append((module, cls))
        column_lines: list[str] = []
        composite_match = re.search(r"PRIMARY KEY \(([^)]+)\)", body)
        composite_pk = (
            [item.strip() for item in composite_match.group(1).split(",")]
            if composite_match
            else []
        )
        table_args: list[str] = []
        for raw_line in body.splitlines():
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            pk_match = re.fullmatch(r"PRIMARY KEY \(([^)]+)\)", line)
            if pk_match:
                continue
            match = re.match(r"(\w+)\s+([A-Z]+(?:\(\d+\))?|\w+_t)\s*(.*)", line)
            if not match:
                raise ValueError(f"Unsupported DDL in {table}: {line}")
            name, sql_type, remainder = match.groups()
            nullable = "NOT NULL" not in remainder and "PRIMARY KEY" not in remainder
            is_pk = "PRIMARY KEY" in remainder or name in composite_pk
            is_unique = "UNIQUE" in remainder
            args: list[str] = []
            annotation: str
            if sql_type == "UUID":
                annotation = "UUID"
                args.append("Uuid()")
            elif sql_type.startswith("VARCHAR"):
                annotation = "str"
                length = re.search(r"\((\d+)\)", sql_type)
                args.append(f"String({length.group(1)})" if length else "String()")
            elif sql_type == "TIMESTAMPTZ":
                annotation = "datetime"
                args.append("DateTime(timezone=True)")
            elif sql_type == "INTEGER":
                annotation = "int"
                args.append("Integer()")
            elif sql_type in enums:
                annotation = "str"
                values = ", ".join(repr(value) for value in enums[sql_type])
                args.append(f"Enum({values}, name={sql_type!r})")
            else:
                raise ValueError(f"Unsupported type {sql_type} in {table}.{name}")

            fk = foreign_keys.get((table, name))
            inline_fk = re.search(r"REFERENCES (\w+)\((\w+)\)", remainder)
            if fk:
                args.append(f"ForeignKey({fk[1]!r}, name={fk[0]!r})")
            elif inline_fk:
                args.append(f"ForeignKey({inline_fk.group(1) + '.' + inline_fk.group(2)!r})")
            options = [f"nullable={nullable!r}"]
            if is_pk:
                options.append("primary_key=True")
            if is_unique:
                options.append("unique=True")
            if "DEFAULT gen_random_uuid()" in remainder:
                options.append('server_default=text("gen_random_uuid()")')
            default_match = re.search(r"DEFAULT (\d+)", remainder)
            if default_match:
                options.append(f'server_default=text("{default_match.group(1)}")')
            mapped_type = annotation if not nullable else f"{annotation} | None"
            all_args = ", ".join(args + options)
            column_lines.append(f"    {name}: Mapped[{mapped_type}] = mapped_column({all_args})")

        for constraint, columns in unique_constraints.get(table, []):
            rendered = ", ".join(repr(column) for column in columns)
            table_args.append(f"UniqueConstraint({rendered}, name={constraint!r})")
        for constraint, expression in checks.get(table, []):
            table_args.append(f"CheckConstraint({expression!r}, name={constraint!r})")
        for name, columns in indexes.get(table, []):
            rendered = ", ".join(repr(column) for column in columns)
            table_args.append(f"Index({name!r}, {rendered})")

        args_block = ""
        if table_args:
            args_block = (
                "    __table_args__ = (\n"
                + "\n".join(f"        {item}," for item in table_args)
                + "\n    )\n\n"
            )
        content = (
            "# Generated from ECOM Physical Data Model v1.3. Do not edit manually.\n"
            "from datetime import datetime\n"
            "from uuid import UUID\n\n"
            "from sqlalchemy import (\n"
            "    CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String,\n"
            "    UniqueConstraint, Uuid, text,\n"
            ")\n"
            "from sqlalchemy.orm import Mapped, mapped_column\n\n"
            "from app.infrastructure.persistence.base import BaseEntity\n\n\n"
            f"class {cls}(BaseEntity):\n"
            f"    __tablename__ = {table!r}\n\n"
            f"{args_block}" + "\n".join(column_lines) + "\n"
        )
        (output_dir / f"{module}.py").write_text(content)

    init_lines = ["# Generated model registry.\n"]
    for module, cls in modules:
        init_lines.append(f"from app.infrastructure.persistence.models.{module} import {cls}\n")
    init_lines.append("\n__all__ = [\n")
    init_lines.extend(f"    {cls!r},\n" for _, cls in modules)
    init_lines.append("]\n")
    (output_dir / "__init__.py").write_text("".join(init_lines))

    repositories_dir = output_dir.parent / "repositories"
    repositories_dir.mkdir(parents=True, exist_ok=True)
    repository_init = ["# Generated repository registry.\n"]
    registry_entries: list[str] = []
    for module, cls in modules:
        repository_class = f"{cls}Repository"
        repository_module = f"{module}_repository"
        repository_content = (
            "# Generated persistence-only repository. Do not add business logic.\n"
            f"from app.infrastructure.persistence.models.{module} import {cls}\n"
            "from app.infrastructure.persistence.repositories.base_repository import BaseRepository\n\n\n"
            f"class {repository_class}(BaseRepository[{cls}]):\n"
            f"    model_type = {cls}\n"
        )
        (repositories_dir / f"{repository_module}.py").write_text(repository_content)
        repository_init.append(
            f"from app.infrastructure.persistence.repositories.{repository_module} "
            f"import {repository_class}\n"
        )
        registry_entries.append(f"    {cls}: {repository_class},\n")
    repository_init.append(
        "\nfrom app.infrastructure.persistence.models import *  # noqa: E402,F403\n\n"
        "REPOSITORY_TYPES = {\n"
    )
    repository_init.extend(registry_entries)
    repository_init.append("}\n")
    (repositories_dir / "__init__.py").write_text("".join(repository_init))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("sql", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    generate(args.sql, args.output)


if __name__ == "__main__":
    main()
