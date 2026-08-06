from collections.abc import Sequence
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.base import BaseEntity

ModelT = TypeVar("ModelT", bound=BaseEntity)


class BaseRepository[ModelT: BaseEntity]:
    """Generic persistence operations with no business decisions."""

    model_type: type[ModelT]

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        return entity

    def add_all(self, entities: Sequence[ModelT]) -> None:
        self._session.add_all(entities)

    def get(self, identifier: UUID | tuple[UUID, ...]) -> ModelT | None:
        return self._session.get(self.model_type, identifier)

    def list(self, *, offset: int = 0, limit: int = 100) -> Sequence[ModelT]:
        statement = select(self.model_type).offset(offset).limit(limit)
        return self._session.scalars(statement).all()

    def delete(self, entity: ModelT) -> None:
        self._session.delete(entity)

    def exists(self, identifier: UUID | tuple[UUID, ...]) -> bool:
        return self.get(identifier) is not None
