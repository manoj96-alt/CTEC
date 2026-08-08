from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class Container:
    """Composition root for dependencies implemented by the current layer."""

    settings: Settings


def build_container() -> Container:
    return Container(settings=get_settings())
