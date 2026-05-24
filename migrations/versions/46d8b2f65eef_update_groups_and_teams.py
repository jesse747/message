"""Update groups and teams

Revision ID: 46d8b2f65eef
Revises: a00b3b44c7e6
Create Date: 2026-05-24 14:07:09.544465

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46d8b2f65eef'
down_revision = 'a00b3b44c7e6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_public', sa.Boolean(), nullable=True))
        batch_op.drop_column('team_id')

    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.add_column(sa.Column('team_admin_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_teams_team_admin_id', 'persons', ['team_admin_id'], ['id'], ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.drop_constraint('fk_teams_team_admin_id', type_='foreignkey')
        batch_op.drop_column('team_admin_id')

    with op.batch_alter_table('groups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('team_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_groups_team_id_downgrade', 'teams', ['team_id'], ['id'])
        batch_op.drop_column('is_public')

    # ### end Alembic commands ###
