# Generated from ECOM Physical Data Model v1.3. Do not edit manually.
from uuid import UUID

from sqlalchemy import (
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.persistence.base import BaseEntity


class Country(BaseEntity):
    __tablename__ = "countries"

    __table_args__ = (
        Index("idx_countries_country_name", "country_name"),
        Index("idx_countries_iso2_code", "iso2_code"),
        Index("idx_countries_iso3_code", "iso3_code"),
    )

    country_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    country_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    iso2_code: Mapped[str] = mapped_column(String(2), nullable=False, unique=True)
    iso3_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
