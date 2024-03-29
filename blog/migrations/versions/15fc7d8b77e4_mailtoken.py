"""mailtoken

Revision ID: 15fc7d8b77e4
Revises: 92e991128d06
Create Date: 2020-10-24 02:34:12.989585

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '15fc7d8b77e4'
down_revision = '92e991128d06'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.create_table('mail_token',
	sa.Column('id', sa.Integer(), nullable=False),
	sa.Column('created_at', sa.DateTime(), nullable=False),
	sa.Column('updated_at', sa.DateTime(), nullable=True),
	sa.Column('owner_id', sa.Integer(), nullable=False),
	sa.Column('key', sa.String(length=10), nullable=False),
	sa.Column('type', sa.String(length=30), nullable=False),
	sa.Column('expires_at', sa.DateTime(), nullable=False),
	sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
	sa.PrimaryKeyConstraint('id'),
	sa.UniqueConstraint('key')
	)
	# ### end Alembic commands ###


def downgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.drop_table('mail_token')
	# ### end Alembic commands ###
