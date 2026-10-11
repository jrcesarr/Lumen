"""A garantia mais importante do produto: um condominio nunca ve dados de outro.

Estes testes falam direto com o banco como app_backend, sem passar pela API. Assim
provam que o isolamento vem do Postgres e nao de um WHERE que alguem pode esquecer.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.factories import criar_cenario


async def _carimbar(conn, **gucs):
    for nome, valor in gucs.items():
        await conn.execute(
            text("SELECT set_config(:n, :v, true)"), {"n": f"app.{nome}", "v": str(valor)}
        )


async def test_guarda_conexao_respeita_rls(engine):
    """Se alguem trocar a DATABASE_URL por um superusuario, todos os testes abaixo mentem."""
    async with engine.connect() as conn:
        linha = (
            await conn.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            )
        ).one()
    assert linha == (False, False)


async def test_sem_carimbo_nao_ve_nada(admin, engine):
    criar_cenario(admin)
    async with engine.begin() as conn:
        for tabela in ["condominios", "unidades", "areas_comuns", "vinculos", "usuarios"]:
            total = (await conn.execute(text(f"SELECT count(*) FROM {tabela}"))).scalar()
            assert total == 0, tabela


async def test_condominio_a_nao_ve_b(admin, engine):
    c = criar_cenario(admin)
    async with engine.begin() as conn:
        await _carimbar(conn, condominio_id=c.cond_a, usuario_id=c.sindico_a)
        unidades = (await conn.execute(text("SELECT condominio_id FROM unidades"))).scalars().all()
        areas = (await conn.execute(text("SELECT condominio_id FROM areas_comuns"))).scalars().all()
    assert set(unidades) == {c.cond_a} and len(unidades) == 2
    assert set(areas) == {c.cond_a}


async def test_nao_grava_em_outro_condominio(admin, engine):
    c = criar_cenario(admin)
    with pytest.raises(DBAPIError, match="row-level security"):
        async with engine.begin() as conn:
            await _carimbar(conn, condominio_id=c.cond_a, usuario_id=c.sindico_a)
            await conn.execute(
                text(
                    "INSERT INTO areas_comuns (id, condominio_id, nome)"
                    " VALUES (gen_random_uuid(), :b, 'Invasao')"
                ),
                {"b": c.cond_b},
            )


async def test_update_em_outro_condominio_nao_afeta_nada(admin, engine):
    c = criar_cenario(admin)
    async with engine.begin() as conn:
        await _carimbar(conn, condominio_id=c.cond_a, usuario_id=c.sindico_a)
        resultado = await conn.execute(
            text("UPDATE unidades SET numero = 'X' WHERE condominio_id = :b"), {"b": c.cond_b}
        )
    assert resultado.rowcount == 0


async def test_vinculo_nao_pode_apontar_unidade_de_outro_condominio(admin):
    c = criar_cenario(admin)
    import psycopg

    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        admin.execute(
            "INSERT INTO vinculos (id, usuario_id, condominio_id, unidade_id, papel)"
            " VALUES (gen_random_uuid(), %s, %s, %s, 'morador')",
            (c.morador_a, c.cond_a, c.unidade_b201),
        )


async def test_auditoria_registra_quem_mudou_o_que(admin, engine):
    c = criar_cenario(admin)
    async with engine.begin() as conn:
        await _carimbar(
            conn,
            condominio_id=c.cond_a,
            usuario_id=c.sindico_a,
            request_id="req-1",
            papel="sindico",
        )
        await conn.execute(
            text("UPDATE areas_comuns SET duracao_max_horas = 4 WHERE nome = 'Churrasqueira'")
        )

    registro = admin.execute(
        "SELECT condominio_id, ator_id, ator_papel, acao, campos_alterados, request_id"
        " FROM auditoria"
    ).fetchall()
    assert registro == [
        (c.cond_a, c.sindico_a, "sindico", "update", ["duracao_max_horas"], "req-1")
    ]


async def test_auditoria_e_imutavel_para_a_api(admin, engine):
    criar_cenario(admin)
    with pytest.raises(DBAPIError, match="permission denied"):
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM auditoria"))


async def test_morador_nao_le_dados_dos_vizinhos(admin, engine):
    c = criar_cenario(admin)
    async with engine.begin() as conn:
        await _carimbar(conn, condominio_id=c.cond_a, usuario_id=c.morador_a, papel="morador")
        emails = (await conn.execute(text("SELECT email FROM usuarios"))).scalars().all()
    assert emails == ["ana@teste.com"]  # so a propria linha


async def test_sindico_le_os_usuarios_do_proprio_condominio(admin, engine):
    c = criar_cenario(admin)
    async with engine.begin() as conn:
        await _carimbar(conn, condominio_id=c.cond_a, usuario_id=c.sindico_a, papel="sindico")
        emails = (await conn.execute(text("SELECT email FROM usuarios"))).scalars().all()
    # Moradores e sindicos do A (inclui a Marina, que tambem e sindica do B), mas ninguem so do B.
    assert sorted(emails) == ["ana@teste.com", "marina@teste.com", "sergio@teste.com"]
