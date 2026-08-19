"""ORM models for the CDD-017 canonical Supply Chain Blueprint requirement
contract (Gate G G2; CDD-017 §6, G2 Persistence and Domain Artifact
Authorization companion). Global, product-owned; no `tenant_id` anywhere
(CDD-017 §9). `Blueprint` carries its own row-level version chain
(`version_number`/`previous_version_id`); no separate `BlueprintVersion`
table exists (CDD-017 §8)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class BlueprintORM(BaseEntity):
    __tablename__ = "blueprints"

    __table_args__ = (
        Index("idx_blueprints_blueprint_name", "blueprint_name"),
        Index("idx_blueprints_lifecycle_state", "lifecycle_state"),
        Index("idx_blueprints_governance_status", "governance_status"),
        Index("idx_blueprints_previous_version_id", "previous_version_id"),
    )

    blueprint_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    blueprint_name: Mapped[str] = mapped_column(String(200), nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(
        Enum("Draft", "Active", "Suspended", "Archived", name="lifecyclestate_t"),
        nullable=False,
    )
    governance_status: Mapped[str] = mapped_column(
        Enum("Proposed", "Approved", "Retired", "Archived", name="governancestatus_t"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer(), nullable=False, server_default=text("1"))
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("blueprints.blueprint_id", name="fk_blueprints_previous_version_id"),
        nullable=True,
    )
    created_by: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_blueprints_created_by"),
        nullable=False,
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    modified_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey("enterprise_entities.enterprise_entity_id", name="fk_blueprints_modified_by"),
        nullable=True,
    )
    modified_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConceptRequirementORM(BaseEntity):
    __tablename__ = "concept_requirements"

    __table_args__ = (
        Index("idx_concept_requirements_blueprint_id", "blueprint_id"),
        Index("idx_concept_requirements_entity_type_id", "entity_type_id"),
    )

    concept_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    blueprint_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("blueprints.blueprint_id", name="fk_concept_requirements_blueprint_id"),
        nullable=False,
    )
    entity_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey("entity_types.entity_type_id", name="fk_concept_requirements_entity_type_id"),
        nullable=False,
    )
    domain_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    obligation: Mapped[str] = mapped_column(
        Enum("REQUIRED", "CONDITIONAL", "OPTIONAL", name="blueprintobligation_t"),
        nullable=False,
    )


class RelationshipRequirementORM(BaseEntity):
    __tablename__ = "relationship_requirements"

    __table_args__ = (
        Index("idx_relationship_requirements_concept_requirement_id", "concept_requirement_id"),
        Index("idx_relationship_requirements_relationship_type_id", "relationship_type_id"),
        Index("idx_relationship_requirements_target_entity_type_id", "target_entity_type_id"),
    )

    relationship_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    concept_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "concept_requirements.concept_requirement_id",
            name="fk_relationship_requirements_concept_requirement_id",
        ),
        nullable=False,
    )
    relationship_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_types.relationship_type_id",
            name="fk_relationship_requirements_relationship_type_id",
        ),
        nullable=False,
    )
    target_entity_type_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "entity_types.entity_type_id",
            name="fk_relationship_requirements_target_entity_type_id",
        ),
        nullable=False,
    )
    obligation: Mapped[str] = mapped_column(
        Enum("REQUIRED", "CONDITIONAL", "OPTIONAL", name="blueprintobligation_t"),
        nullable=False,
    )


class InformationElementRequirementORM(BaseEntity):
    __tablename__ = "information_element_requirements"

    __table_args__ = (
        Index(
            "idx_information_element_requirements_concept_requirement_id",
            "concept_requirement_id",
        ),
    )

    information_element_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(), nullable=False, primary_key=True, server_default=text("gen_random_uuid()")
    )
    concept_requirement_id: Mapped[UUID] = mapped_column(
        Uuid(),
        ForeignKey(
            "concept_requirements.concept_requirement_id",
            name="fk_information_element_requirements_concept_requirement_id",
        ),
        nullable=False,
    )
    element_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    obligation: Mapped[str] = mapped_column(
        Enum("REQUIRED", "CONDITIONAL", "OPTIONAL", name="blueprintobligation_t"),
        nullable=False,
    )
