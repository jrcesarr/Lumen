from uuid import UUID

from pydantic import BaseModel


class VinculoOut(BaseModel):
    condominio_id: UUID
    condominio_nome: str
    papel: str
    unidade_id: UUID | None


class MeOut(BaseModel):
    id: UUID
    nome: str
    email: str
    vinculos: list[VinculoOut]
