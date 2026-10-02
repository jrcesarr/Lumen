"""Tabelas da Carteira: os condominios clientes, suas unidades e areas comuns."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base
from app.shared.ids import uuid7


class Condominio(Base):
    __tablename__ = "condominios"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    nome: Mapped[str]
    cnpj: Mapped[str]
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class Unidade(Base):
    __tablename__ = "unidades"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    condominio_id: Mapped[UUID]
    bloco: Mapped[str] = mapped_column(default="")
    numero: Mapped[str]
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())


class AreaComum(Base):
    __tablename__ = "areas_comuns"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    condominio_id: Mapped[UUID]
    nome: Mapped[str]
    capacidade: Mapped[int | None]
    exige_aprovacao: Mapped[bool] = mapped_column(default=True)
    antecedencia_min_horas: Mapped[int] = mapped_column(default=24)
    duracao_max_horas: Mapped[int] = mapped_column(default=6)
    ativo: Mapped[bool] = mapped_column(default=True)
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())
