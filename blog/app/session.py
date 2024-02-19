import pickle
from uuid import uuid4
from typing import Optional

from flask import Flask, Request, Response
from flask.sessions import SessionMixin, SessionInterface
from flask_login import current_user
from werkzeug.datastructures import CallbackDict

from . import db
from .models import Session
from .utils import get_user_agent


class DatabaseSession(CallbackDict, SessionMixin):
	"""A class, the object of which stores the state of
	the current session in the form of a dictionary for
	subsequent storage in the database."""

	modified = False

	def __init__(self, key: str, /, data: Optional[dict] = None) -> None:
		self.key = key
		self.permanent = True

		def _on_update(self) -> None:
			self.modified = True

		super().__init__(data, _on_update)

	def get_database_object(self) -> Optional[Session]:
		""":return: Could be `None`, when a session is new
		and and has not yet been saved to the database."""
		return Session.query.filter_by(key=self.key).first()


class DatabaseSessionInterface(SessionInterface):
	"""Interface that implements the necessary things to
	manage a session on the server side in the database."""

	serializer = pickle
	session_class = DatabaseSession
	pickle_based = True

	@staticmethod
	def _generate_key() -> str:
		return str(uuid4())

	def open_session(self, app: Flask, request: Request) -> DatabaseSession:  # type: ignore
		key = request.cookies.get(app.session_cookie_name, type=str)

		if not key:
			key = self._generate_key()
			return self.session_class(key)

		session = Session.query.filter_by(key=key).first()

		if session is not None:
			if session.expired:
				db.session.delete(session)
				db.session.commit()
			else:
				data = self.serializer.loads(session.data)
				return self.session_class(key, data=data)

		return self.session_class(key)

	def save_session(self, app: Flask, obj: SessionMixin, response: Response) -> None:
		db_obj = Session.query.filter_by(key=obj.key).first()  # type: ignore
		path = self.get_cookie_path(app)
		domain = self.get_cookie_domain(app)

		if not obj:
			if obj.modified:
				response.delete_cookie(app.session_cookie_name,
   									domain=domain, path=path)
				if db_obj is not None:
					db.session.delete(db_obj)
					db.session.commit()
			return

		secure = self.get_cookie_secure(app)
		httponly = self.get_cookie_httponly(app)
		samesite = self.get_cookie_samesite(app)
		expires_at = self.get_expiration_time(app, obj)

		if db_obj is None:
			db_obj = Session(key=obj.key)  # type: ignore
			db.session.add(db_obj)

		db_obj.expires_at = expires_at
		db_obj.agent = get_user_agent()
		db_obj.data = self.serializer.dumps(dict(obj))
		db_obj.user = current_user if current_user.is_authenticated else None
		db.session.commit()

		response.set_cookie(app.session_cookie_name, obj.key,  # type: ignore
							domain=domain, secure=secure, httponly=httponly,
							path=path, samesite=samesite, expires=expires_at)
