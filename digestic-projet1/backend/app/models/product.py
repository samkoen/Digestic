import dataclasses
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class Product:
    id: str
    name: str
    wholesale_unit_price: float
    vat_rate: float
    units_per_carton: int
    code: Optional[str] = None
    ean: Optional[str] = None
    description: Optional[str] = None
    currency: str = "EUR"
    is_default_for_billing: bool = False
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in names})
