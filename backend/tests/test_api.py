import jwt

from tests.conftest import JWT_SECRET
from tests.factories import criar_cenario, headers, token


async def test_health(client):
    resposta = await client.get("/health")
    assert resposta.status_code == 200
    assert "X-Request-Id" in resposta.headers


async def test_sem_token_401_com_envelope(client):
    resposta = await client.get("/api/v1/unidades")
    assert resposta.status_code == 401
    corpo = resposta.json()
    assert set(corpo) == {"detail", "request_id"}
    assert corpo["request_id"] == resposta.headers["X-Request-Id"]


async def test_token_expirado_401(admin, client):
    c = criar_cenario(admin)
    h = {"Authorization": f"Bearer {token(c.morador_a, minutos=-1)}"}
    assert (await client.get("/api/v1/unidades", headers=h)).status_code == 401


async def test_token_sem_exp_ou_sub_401(admin, client):
    c = criar_cenario(admin)
    base = {"aud": "authenticated", "iss": "http://supabase.teste/auth/v1"}
    sem_exp = jwt.encode({**base, "sub": str(c.morador_a)}, JWT_SECRET, algorithm="HS256")
    sem_sub = jwt.encode({**base, "exp": 4102444800}, JWT_SECRET, algorithm="HS256")
    for t in (sem_exp, sem_sub):
        h = {"Authorization": f"Bearer {t}"}
        assert (await client.get("/api/v1/unidades", headers=h)).status_code == 401


async def test_token_com_audience_errada_401(admin, client):
    c = criar_cenario(admin)
    h = {"Authorization": f"Bearer {token(c.morador_a, aud='outro')}"}
    assert (await client.get("/api/v1/unidades", headers=h)).status_code == 401


async def test_me_lista_todos_os_vinculos(admin, client):
    c = criar_cenario(admin)
    resposta = await client.get("/api/v1/me", headers=headers(c.multi))
    assert resposta.status_code == 200
    vinculos = {(v["condominio_nome"], v["papel"]) for v in resposta.json()["vinculos"]}
    assert vinculos == {("Residencial Aurora", "morador"), ("Edificio Boreal", "sindico")}


async def test_multi_vinculo_sem_header_400(admin, client):
    c = criar_cenario(admin)
    assert (await client.get("/api/v1/unidades", headers=headers(c.multi))).status_code == 400


async def test_header_de_condominio_sem_vinculo_403(admin, client):
    c = criar_cenario(admin)
    resposta = await client.get("/api/v1/unidades", headers=headers(c.morador_a, c.cond_b))
    assert resposta.status_code == 403


async def test_sem_vinculo_403(admin, client):
    c = criar_cenario(admin)
    assert (await client.get("/api/v1/unidades", headers=headers(c.sem_vinculo))).status_code == 403


async def test_papel_muda_conforme_condominio_ativo(admin, client):
    """A mesma pessoa e moradora no A (ve so a sua unidade) e sindica no B (ve todas)."""
    c = criar_cenario(admin)
    no_a = await client.get("/api/v1/unidades", headers=headers(c.multi, c.cond_a))
    no_b = await client.get("/api/v1/unidades", headers=headers(c.multi, c.cond_b))
    assert [u["id"] for u in no_a.json()] == [str(c.unidade_a102)]
    assert [u["id"] for u in no_b.json()] == [str(c.unidade_b201)]


async def test_sindico_ve_todas_as_unidades_do_seu_condominio(admin, client):
    c = criar_cenario(admin)
    resposta = await client.get("/api/v1/unidades", headers=headers(c.sindico_a))
    assert {u["numero"] for u in resposta.json()} == {"101", "102"}


async def test_morador_nao_cria_area_comum_403(admin, client):
    c = criar_cenario(admin)
    resposta = await client.post(
        "/api/v1/areas-comuns", json={"nome": "Piscina"}, headers=headers(c.morador_a)
    )
    assert resposta.status_code == 403


async def test_sindico_cria_area_e_auditoria_registra(admin, client):
    c = criar_cenario(admin)
    resposta = await client.post(
        "/api/v1/areas-comuns",
        json={"nome": "Piscina", "capacidade": 20},
        headers=headers(c.sindico_a),
    )
    assert resposta.status_code == 201
    acao, ator, cond = admin.execute(
        "SELECT acao, ator_id, condominio_id FROM auditoria"
    ).fetchone()
    assert (acao, ator, cond) == ("insert", c.sindico_a, c.cond_a)


async def test_area_com_nome_repetido_409(admin, client):
    c = criar_cenario(admin)
    resposta = await client.post(
        "/api/v1/areas-comuns", json={"nome": "Churrasqueira"}, headers=headers(c.sindico_a)
    )
    assert resposta.status_code == 409


async def test_validacao_422_com_envelope(admin, client):
    c = criar_cenario(admin)
    resposta = await client.post(
        "/api/v1/areas-comuns", json={"nome": ""}, headers=headers(c.sindico_a)
    )
    assert resposta.status_code == 422
    assert "request_id" in resposta.json()
