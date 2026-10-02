from datetime import datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class ReservaIn(BaseModel):
    area_id: UUID
    unidade_id: UUID
    # AwareDatetime: exige fuso horario. "2026-10-10T14:00" sem fuso e recusado (422),
    # porque nao da para saber se e horario de Brasilia ou UTC.
    inicio: AwareDatetime
    fim: AwareDatetime


class RecusaIn(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    area_id: UUID
    unidade_id: UUID
    solicitada_por: UUID
    inicio: datetime
    fim: datetime
    status: str
    motivo_recusa: str | None
