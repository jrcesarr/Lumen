"""Formato dos dados que entram e saem da API (contratos), separado das tabelas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UnidadeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bloco: str
    numero: str


class AreaComumIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    capacidade: int | None = Field(default=None, gt=0)
    exige_aprovacao: bool = True
    antecedencia_min_horas: int = Field(default=24, ge=0)
    duracao_max_horas: int = Field(default=6, gt=0)


class AreaComumOut(AreaComumIn):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
