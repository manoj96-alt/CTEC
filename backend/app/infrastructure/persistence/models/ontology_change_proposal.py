"""ORM model for `ontology_change_proposals` (Gate M; CDD-028 §12, §28; Gate
M Artifact Authorization v1.1 §4.2, §9). Non-canonical: this table confers
no ontology authority and is never read by `app.domain.ontology.resolver`.
No `tenant_id` (CDD-028 §10 -- canonical ontology carries no tenant
dimension). `proposed_by`/`approved_by`/`rejected_by`/`published_by` are
plain strings with no FK -- never `enterprise_entities`-constrained (AA
v1.1 §15, §17).

`uq_ontology_change_proposals_approved_concept_name` and
`uq_ontology_change_proposals_approved_relationship_name` are PostgreSQL
partial unique indexes (`WHERE status IN ('Approved','Published')`) --
mirroring `uq_semantic_mappings_approved_source_field`'s own technique --
preventing a second proposal from ever reaching `Approved` for an
already-claimed net-new name (AA v1.1 §14)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class OntologyChangeProposalORM(BaseEntity):
    __tablename__ = "ontology_change_proposals"

    __table_args__ = (
        Index("idx_ontology_change_proposals_status", "status"),
        Index("idx_ontology_change_proposals_proposal_kind", "proposal_kind"),
        Index("idx_ontology_change_proposals_proposed_by", "proposed_by"),
        Index("idx_ontology_change_proposals_proposed_on", "proposed_on"),
        Index(
            "uq_ontology_change_proposals_approved_concept_name",
            "proposed_entity_type_name",
            unique=True,
            postgresql_where=text(
                "proposal_kind = 'CreateConcept' AND status IN ('Approved', 'Published')"
            ),
        ),
        Index(
            "uq_ontology_change_proposals_approved_relationship_name",
            "proposed_relationship_type_name",
            unique=True,
            postgresql_where=text(
                "proposal_kind = 'CreateRelationship' AND status IN ('Approved', 'Published')"
            ),
        ),
    )

    ontology_change_proposal_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    proposal_kind: Mapped[str] = mapped_column(
        Enum("CreateConcept", "CreateRelationship", name="proposalkind_t"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("Proposed", "Approved", "Rejected", "Published", name="proposalstatus_t"),
        nullable=False,
    )
    proposed_entity_type_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    proposed_definition: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    proposed_relationship_type_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    proposed_source_entity_type_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "entity_types.entity_type_id",
            name="fk_ontology_change_proposals_proposed_source_entity_type_id",
        ),
        nullable=True,
    )
    proposed_target_entity_type_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "entity_types.entity_type_id",
            name="fk_ontology_change_proposals_proposed_target_entity_type_id",
        ),
        nullable=True,
    )
    proposed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    proposed_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    approved_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rejected_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_entity_type_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "entity_types.entity_type_id",
            name="fk_ontology_change_proposals_published_entity_type_id",
        ),
        nullable=True,
    )
    published_relationship_type_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        ForeignKey(
            "relationship_types.relationship_type_id",
            name="fk_ontology_change_proposals_published_relationship_type_id",
        ),
        nullable=True,
    )
