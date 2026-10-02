from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db import Base
from app.shared.ids import uuid7


class Reserva(Base):
    __tablename__ = "reservas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    condominio_id: Mapped[UUID]
    area_id: Mapped[UUID]
    unidade_id: Mapped[UUID]
    solicitada_por: Mapped[UUID]
    inicio: Mapped[datetime]
    fim: Mapped[datetime]
    status: Mapped[str] = mapped_column(default="pendente")
    decidida_por: Mapped[UUID | None]
    decidida_em: Mapped[datetime | None]
    motivo_recusa: Mapped[str | None]
    cancelada_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(server_default=func.now())
