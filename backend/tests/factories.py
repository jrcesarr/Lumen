"""Cenario padrao: dois condominios (A e B) para provar o isolamento entre eles."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.shared.ids import uuid7
from tests.conftest import JWT_SECRET


@dataclass
class Cenario:
    cond_a: UUID
    cond_b: UUID
    unidade_a101: UUID
    unidade_a102: UUID
    unidade_b201: UUID
    morador_a: UUID  # mora no A101
    sindico_a: UUID
    morador_b: UUID
    multi: UUID  # morador no A102 e sindico do B
    sem_vinculo: UUID
    area_a: UUID  # Churrasqueira do A (exige aprovacao, 24h de antecedencia, max 6h)
    area_b: UUID


def criar_cenario(admin) -> Cenario:
    c = Cenario(*(uuid7() for _ in range(12)))
    admin.execute(
        "INSERT INTO condominios (id, nome, cnpj) VALUES (%s, 'Residencial Aurora', '111'),"
        " (%s, 'Edificio Boreal', '222')",
        (c.cond_a, c.cond_b),
    )
    admin.execute(
        "INSERT INTO unidades (id, condominio_id, bloco, numero) VALUES"
        " (%s, %s, 'A', '101'), (%s, %s, 'A', '102'), (%s, %s, '', '201')",
        (c.unidade_a101, c.cond_a, c.unidade_a102, c.cond_a, c.unidade_b201, c.cond_b),
    )
    for uid, nome in [
        (c.morador_a, "Ana"),
        (c.sindico_a, "Sergio"),
        (c.morador_b, "Bruno"),
        (c.multi, "Marina"),
        (c.sem_vinculo, "Zeca"),
    ]:
        admin.execute(
            "INSERT INTO usuarios (id, nome, email) VALUES (%s, %s, %s)",
            (uid, nome, f"{nome.lower()}@teste.com"),
        )
    for usuario, cond, unidade, papel in [
        (c.morador_a, c.cond_a, c.unidade_a101, "morador"),
        (c.sindico_a, c.cond_a, None, "sindico"),
        (c.morador_b, c.cond_b, c.unidade_b201, "morador"),
        (c.multi, c.cond_a, c.unidade_a102, "morador"),
        (c.multi, c.cond_b, None, "sindico"),
    ]:
        admin.execute(
            "INSERT INTO vinculos (id, usuario_id, condominio_id, unidade_id, papel)"
            " VALUES (%s, %s, %s, %s, %s)",
            (uuid7(), usuario, cond, unidade, papel),
        )
    admin.execute(
        "INSERT INTO areas_comuns (id, condominio_id, nome) VALUES"
        " (%s, %s, 'Churrasqueira'), (%s, %s, 'Salao')",
        (c.area_a, c.cond_a, c.area_b, c.cond_b),
    )
    admin.execute("TRUNCATE auditoria")  # o seed nao interessa aos testes de auditoria
    return c


def token(usuario_id: UUID, *, minutos: int = 5, **extra) -> str:
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "aud": "authenticated",
        "iss": "http://supabase.teste/auth/v1",
        "iat": agora,
        "exp": agora + timedelta(minutes=minutos),
        **extra,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def headers(usuario_id: UUID, condominio_id: UUID | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token(usuario_id)}"}
    if condominio_id:
        h["X-Condominio-Id"] = str(condominio_id)
    return h
