"""oauth sid provider unique

Revision ID: da74cd8f617a
Revises: 2396bda10371
Create Date: 2020-11-22 15:49:03.277441

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'da74cd8f617a'
down_revision = '2396bda10371'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.create_unique_constraint(None, 'flask_dance_oauth', ['social_id', 'provider'])
	# ### end Alembic commands ###


def downgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.drop_constraint(None, 'flask_dance_oauth', type_='unique')
	# ### end Alembic commands ###