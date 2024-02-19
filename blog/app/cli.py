import os

import click
from flask import Flask

from . import db
from .models import User


def register_models_cli(app: Flask) -> None:
	@app.cli.group()
	def create() -> None:
		"""Creates new model objects"""
		pass

	@create.command()
	@click.option("--email", prompt="Enter your email", type=str)
	@click.option("--username", prompt="Enter your username", type=str)
	@click.password_option("--password", prompt="Enter your password", type=str)
	def admin(email: str, username: str, password: str) -> None:
		new_user = User(email=email, username=username, is_staff=True, email_is_confirmed=True)
		new_user.set_password(password)
		db.session.add(new_user)
		db.session.commit()


def register_babel_cli(app: Flask) -> None:
	messages_path = app.config['BASE_DIR'].joinpath("messages.pot")

	@app.cli.group()
	def translate() -> None:
		"""Translation and localization commands"""
		pass

	@translate.command()
	@click.argument("language", type=str)
	def init(language: str) -> None:
		if os.system("pybabel extract -F app/babel.cfg -k _l -o app/messages.pot ."):
			raise RuntimeError("Extract command failed.")
		elif os.system("pybabel init -i app/messages.pot -d app/translations -l %s" % language):
			raise RuntimeError("Init command failed.")

		messages_path.unlink()

	@translate.command()
	def update() -> None:
		if os.system("pybabel extract -F app/babel.cfg -k _l -o app/messages.pot ."):
			raise RuntimeError("Extract command failed.")
		elif os.system("pybabel update -i app/messages.pot -d app/translations"):
			raise RuntimeError("Update command failed.")

		messages_path.unlink()

	@translate.command()
	def compile() -> None:
		if os.system("pybabel compile -d app/translations"):
			raise RuntimeError("Compile command failed.")
