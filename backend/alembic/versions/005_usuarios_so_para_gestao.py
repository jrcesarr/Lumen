"""Usuarios: so o proprio usuario e quem gerencia o condominio leem e-mail e telefone.

Antes, qualquer pessoa com vinculo no condominio lia os dados de todos os outros.

Revision ID: 005
"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP POLICY usuarios_leitura ON usuarios;
        -- app_papel_atual() traz os papeis do vinculo ja validado pela API (ex.: 'sindico').
        CREATE POLICY usuarios_leitura ON usuarios FOR SELECT
          USING (
            id = app_usuario_atual()
            OR (
              string_to_array(app_papel_atual(), ',') && ARRAY['sindico', 'atendente', 'admin']
              AND EXISTS (
                SELECT 1 FROM vinculos v
                 WHERE v.usuario_id = usuarios.id
                   AND v.condominio_id = app_condominio_atual())));
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP POLICY usuarios_leitura ON usuarios;
        CREATE POLICY usuarios_leitura ON usuarios FOR SELECT
          USING (id = app_usuario_atual() OR EXISTS (
            SELECT 1 FROM vinculos v
             WHERE v.usuario_id = usuarios.id
               AND v.condominio_id = app_condominio_atual()));
        """
    )
