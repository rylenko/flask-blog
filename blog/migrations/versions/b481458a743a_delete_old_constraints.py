"""delete old constraints

Revision ID: b481458a743a
Revises: 19423810ab21
Create Date: 2020-11-14 16:32:05.640663

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b481458a743a'
down_revision = '19423810ab21'
branch_labels = None
depends_on = None


def upgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.drop_constraint('mail_token_key_key', 'mail_token', type_='unique')
	op.drop_constraint('post_slug_key', 'post', type_='unique')
	op.drop_constraint('tag_name_key', 'tag', type_='unique')
	op.drop_constraint('user_email_key', 'user', type_='unique')
	op.drop_constraint('user_secret_key_key', 'user', type_='unique')
	op.drop_constraint('user_username_key', 'user', type_='unique')
	# ### end Alembic commands ###


def downgrade():
	# ### commands auto generated by Alembic - please adjust! ###
	op.create_unique_constraint('user_username_key', 'user', ['username'])
	op.create_unique_constraint('user_secret_key_key', 'user', ['secret_key'])
	op.create_unique_constraint('user_email_key', 'user', ['email'])
	op.create_unique_constraint('tag_name_key', 'tag', ['name'])
	op.create_unique_constraint('post_slug_key', 'post', ['slug'])
	op.create_unique_constraint('mail_token_key_key', 'mail_token', ['key'])
	# ### end Alembic commands ###