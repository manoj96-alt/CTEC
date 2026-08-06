from typing import Any

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class BaseEntity(Base):
    """Typed marker for canonical entity models without invented columns."""

    __abstract__ = True
    __allow_unmapped__ = False

    def as_record(self) -> dict[str, Any]:
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
