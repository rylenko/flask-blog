import secrets
from typing import Any

from flask import Flask, url_for
from flask_login import current_user, FlaskLoginClient

from app import db
from app.models import User


class Client(FlaskLoginClient):
	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)

		with self.session_transaction() as session:
			# Set the values that will bypass the various obstacles
			session['password_was_once_confirmed'] = True


def create_test_user(**kwargs: Any) -> User:
	payload = secrets.token_hex(2)
	rv = User(email="test-user%s@em.ail" % payload,
  			username="test-user" + payload, **kwargs)
	rv.set_password("test-user-password")
	db.session.add(rv)
	db.session.commit()

	return rv


def check_response_ok(client: Client, endpoint: str, **options: Any) -> bool:
	response = client.get(url_for(endpoint, **options))
	return response.status_code == 200


def register_auxiliary_routes(app: Flask, /) -> None:
	@app.route("/is-authenticated/")
	def is_authenticated():
		return str(current_user.is_authenticated)


def check_is_authenticated(client: Client, /) -> bool:
	response = client.get(url_for("is_authenticated"))
	return response.data.decode() == "True"
