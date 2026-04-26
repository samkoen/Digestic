from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class PharmacyComment:
    id: str
    pharmacy_id: str
    text: str
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)
