"""Identidade e Carteira: condominios, unidades, usuarios, papeis, vinculos e areas comuns.

Revision ID: 002
"""

from alembic import op
from app.core.permissions import PAPEIS

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

NOMES_PAPEIS = {
    "morador": "Morador",
    "sindico": "Sindico",
    "porteiro": "Porteiro",
    "prestador": "Prestador de servico",
    "atendente": "Atendente da Lumen",
    "admin": "Administrador da Lumen",
}


def upgrade() -> None:
    # --- Carteira --------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE condominios (
          id uuid PRIMARY KEY,                 -- UUIDv7 gerado pela aplicacao
          nome text NOT NULL,
          cnpj text NOT NULL UNIQUE,
          ativo boolean NOT NULL DEFAULT true,
          criado_em timestamptz NOT NULL DEFAULT now(),
          atualizado_em timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE unidades (
          id uuid PRIMARY KEY,
          condominio_id uuid NOT NULL REFERENCES condominios (id) ON DELETE RESTRICT,
          bloco text NOT NULL DEFAULT '',
          numero text NOT NULL,
          ativo boolean NOT NULL DEFAULT true,
          criado_em timestamptz NOT NULL DEFAULT now(),
          atualizado_em timestamptz NOT NULL DEFAULT now(),
          UNIQUE (condominio_id, bloco, numero),
          -- Permite FKs compostas (unidade_id, condominio_id) nas outras tabelas:
          -- assim e impossivel apontar para uma unidade de OUTRO condominio.
          UNIQUE (id, condominio_id)
        );

        CREATE TABLE areas_comuns (
          id uuid PRIMARY KEY,
          condominio_id uuid NOT NULL REFERENCES condominios (id) ON DELETE RESTRICT,
          nome text NOT NULL,
          capacidade integer CHECK (capacidade > 0),
          exige_aprovacao boolean NOT NULL DEFAULT true,
          antecedencia_min_horas integer NOT NULL DEFAULT 24 CHECK (antecedencia_min_horas >= 0),
          duracao_max_horas integer NOT NULL DEFAULT 6 CHECK (duracao_max_horas > 0),
          ativo boolean NOT NULL DEFAULT true,
          criado_em timestamptz NOT NULL DEFAULT now(),
          atualizado_em timestamptz NOT NULL DEFAULT now(),
          UNIQUE (condominio_id, nome),
          UNIQUE (id, condominio_id)
        );
        """
    )

    # --- Identidade --------------------------------------------------------------
    op.execute(
        """
        -- A pessoa existe independente do predio: sem condominio_id.
        CREATE TABLE usuarios (
          id uuid PRIMARY KEY,                 -- o mesmo id do Supabase Auth
          nome text NOT NULL,
          email text NOT NULL UNIQUE,
          telefone text,
          criado_em timestamptz NOT NULL DEFAULT now(),
          atualizado_em timestamptz NOT NULL DEFAULT now()
        );

        -- Papeis e permissoes sao globais e somente leitura para a aplicacao.
        CREATE TABLE papeis (
          slug text PRIMARY KEY,
          nome text NOT NULL
        );
        CREATE TABLE papel_permissoes (
          papel text NOT NULL REFERENCES papeis (slug) ON DELETE CASCADE,
          permissao text NOT NULL,             -- formato recurso.acao
          PRIMARY KEY (papel, permissao)
        );

        -- A peca central: quem (usuario), onde (condominio), qual apartamento e como (papel).
        CREATE TABLE vinculos (
          id uuid PRIMARY KEY,
          usuario_id uuid NOT NULL REFERENCES usuarios (id) ON DELETE RESTRICT,
          condominio_id uuid NOT NULL REFERENCES condominios (id) ON DELETE RESTRICT,
          unidade_id uuid,
          papel text NOT NULL REFERENCES papeis (slug),
          ativo boolean NOT NULL DEFAULT true,
          criado_em timestamptz NOT NULL DEFAULT now(),
          atualizado_em timestamptz NOT NULL DEFAULT now(),
          FOREIGN KEY (unidade_id, condominio_id) REFERENCES unidades (id, condominio_id),
          -- Morador sempre tem unidade; os outros papeis nunca tem.
          CONSTRAINT unidade_so_para_morador CHECK ((papel = 'morador') = (unidade_id IS NOT NULL)),
          -- NULLS NOT DISTINCT: dois vinculos de sindico (unidade NULL) contam como repetidos.
          CONSTRAINT vinculo_unico UNIQUE NULLS NOT DISTINCT
            (usuario_id, condominio_id, papel, unidade_id)
        );
        CREATE INDEX vinculos_usuario_idx ON vinculos (usuario_id) WHERE ativo;
        """
    )

    # Seed dos papeis ANTES de qualquer RLS (vem do catalogo em app/core/permissions.py).
    for slug, nome in NOMES_PAPEIS.items():
        op.execute(f"INSERT INTO papeis (slug, nome) VALUES ('{slug}', '{nome}')")
        for permissao in sorted(PAPEIS[slug]):
            op.execute(
                f"INSERT INTO papel_permissoes (papel, permissao) "
                f"VALUES ('{slug}', '{permissao.value}')"
            )

    # --- Protecao: grants + RLS + auditoria ----------------------------------------
    op.execute(
        """
        SELECT app_preparar_tabela('unidades');
        SELECT app_preparar_tabela('areas_comuns');
        SELECT app_preparar_tabela('vinculos');
        -- O condominio E o tenant: a policy compara a propria coluna id.
        SELECT app_preparar_tabela('condominios', 'id');

        -- Excecao 1: cada um le os PROPRIOS vinculos mesmo sem condominio carimbado
        -- (e assim que o contexto descobre em quais condominios o usuario esta).
        CREATE POLICY vinculos_proprios ON vinculos FOR SELECT
          USING (usuario_id = app_usuario_atual());

        -- Excecao 2: o seletor de condominio lista os condominios dos meus vinculos.
        CREATE POLICY condominios_dos_meus_vinculos ON condominios FOR SELECT
          USING (EXISTS (
            SELECT 1 FROM vinculos v
             WHERE v.condominio_id = condominios.id
               AND v.usuario_id = app_usuario_atual()
               AND v.ativo));

        -- usuarios nao tem condominio_id: policy propria.
        GRANT SELECT, UPDATE ON usuarios TO app_backend;
        ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
        ALTER TABLE usuarios FORCE ROW LEVEL SECURITY;
        CREATE POLICY usuarios_leitura ON usuarios FOR SELECT
          USING (id = app_usuario_atual() OR EXISTS (
            SELECT 1 FROM vinculos v
             WHERE v.usuario_id = usuarios.id
               AND v.condominio_id = app_condominio_atual()));
        CREATE POLICY usuarios_edita_o_proprio ON usuarios FOR UPDATE
          USING (id = app_usuario_atual()) WITH CHECK (id = app_usuario_atual());
        CREATE TRIGGER auditoria_trg AFTER INSERT OR UPDATE OR DELETE ON usuarios
          FOR EACH ROW EXECUTE FUNCTION app_auditoria_trg();
        SELECT app_ativar_atualizado_em('usuarios');

        -- Papeis: leitura para a API, alteracao so por migration.
        GRANT SELECT ON papeis, papel_permissoes TO app_backend;
        """
    )

    # Supabase: o perfil em usuarios nasce por trigger quando alguem se cadastra no Auth.
    # SECURITY DEFINER porque no cadastro ainda nao existe carimbo (a RLS barraria).
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('auth.users') IS NOT NULL THEN
            CREATE FUNCTION public.sincronizar_usuario_do_auth() RETURNS trigger
            LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $f$
            BEGIN
              INSERT INTO public.usuarios (id, nome, email)
              VALUES (NEW.id, coalesce(NEW.raw_user_meta_data ->> 'nome', NEW.email), NEW.email)
              ON CONFLICT (id) DO NOTHING;
              RETURN NEW;
            END $f$;
            CREATE TRIGGER sincronizar_usuario AFTER INSERT ON auth.users
              FOR EACH ROW EXECUTE FUNCTION public.sincronizar_usuario_do_auth();
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS sincronizar_usuario ON auth.users;
        DROP FUNCTION IF EXISTS public.sincronizar_usuario_do_auth();
        DROP TABLE vinculos, papel_permissoes, papeis, usuarios, areas_comuns, unidades,
                   condominios;
        """
    )
