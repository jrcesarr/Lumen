"""Base: roles, funcoes de GUC, auditoria e o preparo padrao de tabelas.

Depois desta migration, proteger uma tabela nova e uma linha:
    SELECT app_preparar_tabela('reservas');
(grants + RLS com falha fechada + trigger de auditoria + trigger de atualizado_em)

Revision ID: 001
"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")  # usada pelas reservas (003)

    # --- Roles ---------------------------------------------------------------
    # Sem senha aqui: cada ambiente define a sua por fora (ALTER ROLE ... PASSWORD).
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_backend') THEN
            CREATE ROLE app_backend LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_migrador') THEN
            CREATE ROLE app_migrador LOGIN NOSUPERUSER NOBYPASSRLS;
          END IF;
        END $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_backend")

    # --- Leitura das GUCs (o "carimbo" da transacao) -------------------------
    # current_setting(..., true) devolve NULL se a GUC nao existe; nullif trata ''.
    # NULL numa policy = zero linhas. E isso que faz a RLS "falhar fechada".
    for funcao, guc, tipo in [
        ("app_condominio_atual", "condominio_id", "uuid"),
        ("app_usuario_atual", "usuario_id", "uuid"),
        ("app_request_id", "request_id", "text"),
        ("app_papel_atual", "papel", "text"),
    ]:
        op.execute(
            f"""
            CREATE FUNCTION {funcao}() RETURNS {tipo} LANGUAGE sql STABLE AS $$
              SELECT nullif(current_setting('app.{guc}', true), '')::{tipo}
            $$;
            """
        )

    # --- Auditoria -----------------------------------------------------------
    op.execute(
        """
        CREATE TABLE auditoria (
          id bigserial PRIMARY KEY,
          condominio_id uuid,
          ocorrido_em timestamptz NOT NULL DEFAULT now(),
          ator_id uuid,
          ator_papel text,
          origem text NOT NULL CHECK (origem IN ('trigger', 'app')),
          tabela text,
          registro_id uuid,
          acao text NOT NULL,
          dados_antes jsonb,
          dados_depois jsonb,
          campos_alterados text[],
          request_id text
        );
        CREATE INDEX auditoria_condominio_idx ON auditoria (condominio_id, ocorrido_em DESC);
        CREATE INDEX auditoria_registro_idx ON auditoria (tabela, registro_id);
        CREATE INDEX auditoria_ator_idx ON auditoria (ator_id, ocorrido_em DESC);

        -- Log imutavel: a aplicacao so pode inserir e ler, nunca alterar ou apagar.
        GRANT INSERT, SELECT ON auditoria TO app_backend;
        GRANT USAGE ON SEQUENCE auditoria_id_seq TO app_backend;

        ALTER TABLE auditoria ENABLE ROW LEVEL SECURITY;
        ALTER TABLE auditoria FORCE ROW LEVEL SECURITY;
        CREATE POLICY auditoria_leitura ON auditoria FOR SELECT
          USING (condominio_id = app_condominio_atual());
        CREATE POLICY auditoria_escrita ON auditoria FOR INSERT WITH CHECK (true);
        """
    )

    # Trigger generica: grava o antes e o depois de toda alteracao.
    # TG_ARGV[0] = nome da coluna do condominio (ou nada, para tabelas globais).
    op.execute(
        """
        CREATE FUNCTION app_auditoria_trg() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
          antes jsonb := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END;
          depois jsonb := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END;
          linha jsonb := coalesce(depois, antes);
          condominio uuid;
          alterados text[];
        BEGIN
          IF TG_NARGS > 0 THEN
            condominio := (linha ->> TG_ARGV[0])::uuid;
          ELSE
            condominio := app_condominio_atual();
          END IF;
          IF TG_OP = 'UPDATE' THEN
            SELECT array_agg(chave) INTO alterados
              FROM jsonb_object_keys(depois) AS chave
             WHERE depois -> chave IS DISTINCT FROM antes -> chave
               AND chave <> 'atualizado_em';
          END IF;
          INSERT INTO auditoria (condominio_id, ator_id, ator_papel, origem, tabela,
                                 registro_id, acao, dados_antes, dados_depois,
                                 campos_alterados, request_id)
          VALUES (condominio, app_usuario_atual(), app_papel_atual(), 'trigger', TG_TABLE_NAME,
                  (linha ->> 'id')::uuid, lower(TG_OP), antes, depois, alterados,
                  app_request_id());
          RETURN NULL;
        END $$;
        """
    )

    op.execute(
        """
        CREATE FUNCTION app_atualizado_em_trg() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          NEW.atualizado_em := now();
          RETURN NEW;
        END $$;
        """
    )

    # --- Preparo padrao de tabelas -------------------------------------------
    op.execute(
        """
        CREATE FUNCTION app_conceder_grants(tabela text) RETURNS void LANGUAGE plpgsql AS $$
        DECLARE papel text;
        BEGIN
          EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON %I TO app_backend', tabela);
          -- No Supabase, estes roles acessam o banco pela API automatica (PostgREST).
          -- Nenhuma tabela de negocio pode ficar visivel por la: tudo passa pela nossa API.
          FOREACH papel IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = papel) THEN
              EXECUTE format('REVOKE ALL ON %I FROM %I', tabela, papel);
            END IF;
          END LOOP;
        END $$;

        CREATE FUNCTION app_ativar_rls(tabela text, coluna text DEFAULT 'condominio_id')
        RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
          EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tabela);
          EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', tabela);
          EXECUTE format(
            'CREATE POLICY isolamento_condominio ON %I
               USING (%I = app_condominio_atual())
               WITH CHECK (%I = app_condominio_atual())',
            tabela, coluna, coluna);
        END $$;

        CREATE FUNCTION app_ativar_auditoria(tabela text, coluna text DEFAULT 'condominio_id')
        RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
          EXECUTE format(
            'CREATE TRIGGER auditoria_trg AFTER INSERT OR UPDATE OR DELETE ON %I
               FOR EACH ROW EXECUTE FUNCTION app_auditoria_trg(%L)',
            tabela, coluna);
        END $$;

        CREATE FUNCTION app_ativar_atualizado_em(tabela text) RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
          EXECUTE format(
            'CREATE TRIGGER atualizado_em_trg BEFORE UPDATE ON %I
               FOR EACH ROW EXECUTE FUNCTION app_atualizado_em_trg()',
            tabela);
        END $$;

        CREATE FUNCTION app_preparar_tabela(
          tabela text,
          coluna text DEFAULT 'condominio_id',
          tem_atualizado_em boolean DEFAULT true
        ) RETURNS void LANGUAGE plpgsql AS $$
        BEGIN
          PERFORM app_conceder_grants(tabela);
          PERFORM app_ativar_rls(tabela, coluna);
          PERFORM app_ativar_auditoria(tabela, coluna);
          IF tem_atualizado_em THEN
            PERFORM app_ativar_atualizado_em(tabela);
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP FUNCTION app_preparar_tabela(text, text, boolean);
        DROP FUNCTION app_ativar_atualizado_em(text);
        DROP FUNCTION app_ativar_auditoria(text, text);
        DROP FUNCTION app_ativar_rls(text, text);
        DROP FUNCTION app_conceder_grants(text);
        DROP FUNCTION app_atualizado_em_trg();
        DROP TABLE auditoria;
        DROP FUNCTION app_auditoria_trg();
        DROP FUNCTION app_condominio_atual();
        DROP FUNCTION app_usuario_atual();
        DROP FUNCTION app_request_id();
        DROP FUNCTION app_papel_atual();
        """
    )
