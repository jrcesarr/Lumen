"""Outbox: eventos gravados na mesma transacao do fato que os gerou.

Revision ID: 004
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE outbox (
          id uuid PRIMARY KEY,
          condominio_id uuid NOT NULL REFERENCES condominios (id) ON DELETE RESTRICT,
          tipo text NOT NULL,                   -- ex.: reserva.aprovada
          payload jsonb NOT NULL,
          status text NOT NULL DEFAULT 'pendente'
            CHECK (status IN ('pendente', 'processado', 'falhou')),
          tentativas integer NOT NULL DEFAULT 0,
          proxima_tentativa timestamptz NOT NULL DEFAULT now(),
          ultimo_erro text,
          criado_em timestamptz NOT NULL DEFAULT now(),
          processado_em timestamptz,
          CONSTRAINT processado_registrado
            CHECK ((status = 'processado') = (processado_em IS NOT NULL))
        );

        -- O worker so olha o que esta pendente, na ordem em que aconteceu.
        CREATE INDEX outbox_pendentes_idx ON outbox (proxima_tentativa, criado_em)
          WHERE status = 'pendente';

        -- Sem app_preparar_tabela: a auditoria nao faz sentido para uma fila (cada
        -- tentativa viraria uma linha) e a tabela nao precisa de atualizado_em.
        SELECT app_conceder_grants('outbox');
        SELECT app_ativar_rls('outbox');

        -- O worker nao tem condominio ativo: ele varre todos. Esta policy so vale quando
        -- a transacao e carimbada com papel = 'worker' e so existe nesta tabela.
        CREATE POLICY outbox_worker ON outbox
          USING (app_papel_atual() = 'worker')
          WITH CHECK (app_papel_atual() = 'worker');
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE outbox")
