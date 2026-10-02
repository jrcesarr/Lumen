"""Tabelas da Identidade: a pessoa (usuario) e seus vinculos com condominios."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base
from app.shared.ids import uuid7


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(primary_key=True)  # mesmo id do Supabase Auth
    nome: Mapped[str]
    email: Mapped[str]
    telefone: Mapped[str | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class Vinculo(Base):
    __tablename__ = "vinculos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    usuario_id: Mapped[UUID]
    condominio_id: Mapped[UUID]
    unidade_id: Mapped[UUID | None]
    papel: Mapped[str]
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())
