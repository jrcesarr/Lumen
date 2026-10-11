"""Validacao do JWT emitido pelo Supabase Auth.

Aceita os dois regimes de assinatura do Supabase (igual a SmartFit):
- HS256 com o segredo legado (tambem usado nos testes);
- ES256/RS256 com a chave publica do JWKS do projeto.
Cada ramo passa uma lista fechada de algoritmos para o jwt.decode, o que impede
ataques de confusao de algoritmo (ex.: token com alg "none").
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache

import jwt

from app.core.config import get_settings
from app.shared.errors import NaoAutenticadoError


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: str
    email: str | None


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(get_settings().jwks_url, cache_keys=True, lifespan=3600)


def decodificar_token(token: str) -> UsuarioAutenticado:
    settings = get_settings()
    try:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise NaoAutenticadoError("Token HS256 nao aceito neste ambiente")
            chave, algoritmos = settings.supabase_jwt_secret, ["HS256"]
        elif alg in ("ES256", "RS256"):
            chave, algoritmos = _jwks_client().get_signing_key_from_jwt(token).key, [alg]
        else:
            raise NaoAutenticadoError("Algoritmo de assinatura nao suportado")

        payload = jwt.decode(
            token,
            chave,
            algorithms=algoritmos,
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            # Sem exp o token nunca expiraria; sem sub nao saberiamos de quem e.
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise NaoAutenticadoError("Token invalido ou expirado") from exc

    return UsuarioAutenticado(id=payload["sub"], email=payload.get("email"))


async def decodificar_token_async(token: str) -> UsuarioAutenticado:
    # O cliente JWKS faz I/O sincrono; roda numa thread para nao travar o event loop.
    return await asyncio.to_thread(decodificar_token, token)
