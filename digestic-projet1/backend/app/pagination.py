"""Pagination serveur (liste paginée, total, tris) — utilisable sur d'autres ressources."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 500


@dataclass(frozen=True)
class PageResult(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def normalize_page_input(page: int, page_size: int) -> tuple[int, int]:
    """Borne `page` (≥1) et `page_size` (1..MAX_PAGE_SIZE)."""
    p = max(1, page)
    ps = min(max(1, page_size), MAX_PAGE_SIZE)
    return p, ps


def offset_for_page(page: int, page_size: int) -> int:
    return (page - 1) * page_size
