"""Reservas de areas comuns.

Revision ID: 003
"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE reservas (
          id uuid PRIMARY KEY,
          condominio_id uuid NOT NULL REFERENCES condominios (id) ON DELETE RESTRICT,
          area_id uuid NOT NULL,
          unidade_id uuid NOT NULL,
          solicitada_por uuid NOT NULL REFERENCES usuarios (id),
          inicio timestamptz NOT NULL,
          fim timestamptz NOT NULL,
          status text NOT NULL DEFAULT 'pendente'
            CHECK (status IN ('pendente', 'aprovada', 'recusada', 'cancelada')),
          decidida_por uuid REFERENCES usuarios (id),
          decidida_em timestamptz,
          motivo_recusa text,
          cancelada_em timestamptz,
          criado_em timestamptz NOT NULL DEFAULT now(),
          atualizado_em timestamptz NOT NULL DEFAULT now(),

          -- FKs compostas: area e unidade TEM de ser do mesmo condominio da reserva.
          FOREIGN KEY (area_id, condominio_id) REFERENCES areas_comuns (id, condominio_id),
          FOREIGN KEY (unidade_id, condominio_id) REFERENCES unidades (id, condominio_id),

          CONSTRAINT fim_depois_do_inicio CHECK (fim > inicio),
          CONSTRAINT recusa_tem_motivo
            CHECK (status <> 'recusada' OR length(trim(motivo_recusa)) > 0),
          CONSTRAINT decisao_registrada
            CHECK (status NOT IN ('aprovada', 'recusada') OR decidida_em IS NOT NULL),
          CONSTRAINT cancelamento_registrado
            CHECK ((status = 'cancelada') = (cancelada_em IS NOT NULL)),

          -- A regra mais importante: duas reservas APROVADAS da mesma area nunca se
          -- sobrepoem. Vale mesmo com dois sindicos clicando "aprovar" ao mesmo tempo.
          -- '[)' = intervalo fechado no inicio e aberto no fim: 14h-18h e 18h-22h nao colidem.
          CONSTRAINT sem_sobreposicao EXCLUDE USING gist (
            area_id WITH =,
            tstzrange(inicio, fim, '[)') WITH &&
          ) WHERE (status = 'aprovada')
        );

        CREATE INDEX reservas_area_periodo_idx ON reservas (area_id, inicio);
        CREATE INDEX reservas_unidade_idx ON reservas (unidade_id, inicio DESC);
        CREATE INDEX reservas_pendentes_idx ON reservas (condominio_id, inicio)
          WHERE status = 'pendente';

        SELECT app_preparar_tabela('reservas');
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE reservas")
