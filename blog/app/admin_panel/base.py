from datetime import datetime
from typing import Any, Type, Callable

from flask import abort, Blueprint, current_app
from flask_login import current_user
from flask_admin.model import typefmt
from flask_admin.contrib.sqla import ModelView as BaseModelView

from .. import db
from ..models import BaseModel


DEFAULT_FORMATTERS = typefmt.BASE_FORMATTERS
DEFAULT_FORMATTERS.update({
	datetime: lambda view, value: value.strftime(
		current_app.config['DATETIME_FORMAT'],
	),
})


class AdminRequiredMixin:
	"""A mixin for the `flask_admin.BaseView` that prevents
	users from visiting the page if they are not administrators."""

	def is_accessible(self) -> bool:
		return current_user.is_authenticated and current_user.is_staff

	def inaccessible_callback(self, name: str, **kwargs: Any) -> None:
		abort(404)

	def create_blueprint(self, *args: Any, **kwargs: Any) -> Blueprint:
		self._allow_post_request_everywhere()
		return super().create_blueprint(*args, **kwargs)  # type: ignore

	def _allow_post_request_everywhere(self) -> None:
		"""This is required by the `password_confirm_once_required`
		decorator, which we use in `self._run_view`"""

		for i, url in enumerate(self._urls):  # type: ignore
			*args, methods = url

			if "POST" not in methods:
				methods = (*methods, "POST")
				self._urls[i] = (*args, methods)  # type: ignore

	def _run_view(self, f: Callable, *args: Any, **kwargs: Any) -> Any:
		from ..decorators import password_confirm_once_required
		return password_confirm_once_required(f)(self, *args, **kwargs)


class ModelView(AdminRequiredMixin, BaseModelView):
	model: Type[BaseModel]
	column_type_formatters = DEFAULT_FORMATTERS

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(self.model, db.session, *args, **kwargs)
