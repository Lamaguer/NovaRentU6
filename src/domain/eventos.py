from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Evento:
    nombre: str
    agregado_id: str
    datos: dict = field(default_factory=dict)
    ocurrido_en: datetime = field(default_factory=datetime.now)
