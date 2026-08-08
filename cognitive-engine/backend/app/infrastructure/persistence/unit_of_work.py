from types import TracebackType
from typing import Self, TypeVar, cast

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.persistence.base import BaseEntity
from app.infrastructure.persistence.repositories import REPOSITORY_TYPES
from app.infrastructure.persistence.repositories.base_repository import BaseRepository

ModelT = TypeVar("ModelT", bound=BaseEntity)


class UnitOfWork:
    """Owns one session and all repositories participating in its transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self.session: Session | None = None
        self._repositories: dict[type[BaseEntity], BaseRepository[BaseEntity]] = {}

    def __enter__(self) -> Self:
        self.session = self._session_factory()
        return self

    def repository(self, model_type: type[ModelT]) -> BaseRepository[ModelT]:
        if self.session is None:
            raise RuntimeError("UnitOfWork must be entered before repositories are requested")
        repository: BaseRepository[BaseEntity] | None = self._repositories.get(model_type)
        if repository is None:
            repository_type = REPOSITORY_TYPES[model_type]
            repository = cast(BaseRepository[BaseEntity], repository_type(self.session))
            self._repositories[model_type] = repository
        return cast(BaseRepository[ModelT], repository)

    def commit(self) -> None:
        self._require_session().commit()

    def rollback(self) -> None:
        self._require_session().rollback()

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None
            self._repositories.clear()

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exception_type is not None:
                self.rollback()
        finally:
            self.close()

    def _require_session(self) -> Session:
        if self.session is None:
            raise RuntimeError("UnitOfWork is not active")
        return self.session
