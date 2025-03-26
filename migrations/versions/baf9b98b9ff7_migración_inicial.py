"""Migración inicial

Revision ID: baf9b98b9ff7
Revises: 
Create Date: 2025-03-26 16:17:04.221673

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'baf9b98b9ff7'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute("DROP TABLE IF EXISTS _alembic_tmp_user")  # Solución para evitar duplicate temporary table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("user")]
    constraints = [uc["name"] for uc in inspector.get_unique_constraints("user")]
    
    # Solo agregar la columna 'email' si no existe
    if 'email' not in columns:
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.add_column(sa.Column('email', sa.String(length=120), nullable=True))
    
    # Actualizar registros existentes para asignar un valor a 'email'
    op.execute("UPDATE user SET email = username || '@example.com' WHERE email IS NULL")
    
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Establecer 'email' como NOT NULL
        batch_op.alter_column('email',
               existing_type=sa.String(length=120),
               nullable=False)
        # Crear constraint única solo si aún no existe
        if 'uq_user_email' not in constraints:
            batch_op.create_unique_constraint('uq_user_email', ['email'])
        # Otras alteraciones
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=80),
               type_=sa.String(length=50),
               existing_nullable=False)
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=128),
               existing_nullable=True,
               nullable=False)

def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_email', type_='unique')
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=128),
               existing_nullable=False,
               nullable=True)
        batch_op.alter_column('username',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=80),
               existing_nullable=False)
        batch_op.drop_column('email')
