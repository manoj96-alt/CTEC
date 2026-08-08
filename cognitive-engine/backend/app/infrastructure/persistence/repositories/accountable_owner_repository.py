# Generated persistence-only repository. Do not add business logic.
from app.infrastructure.persistence.models.accountable_owner import AccountableOwner
from app.infrastructure.persistence.repositories.base_repository import BaseRepository


class AccountableOwnerRepository(BaseRepository[AccountableOwner]):
    model_type = AccountableOwner
