from typing import Any, Optional, Callable
from functools import wraps

from flask import abort, url_for, request, session, redirect, render_template
from flask_login import current_user


def _make_condition_decorator(
	f: Callable,
	condition: Callable[[], bool],
	otherwise: Callable[[], Optional[Any]],
	*, return_otherwise: bool = False,
) -> Callable:
	"""
	The decorator that checks that `condition()` returns `True`,
	otherwise uses `otherwise()`. Login required decorator example:

		def login_required(f: Callable) -> Callable:
			return _make_condition_decorator(
				decorated_function,
				lambda: current_user.is_authenticated,
				lambda: abort(403),
		)
	"""

	@wraps(f)
	def wrapper(*args: Any, **kwargs: Any) -> Any:
		if not condition():
			if return_otherwise:
				return otherwise()
			otherwise()
		return f(*args, **kwargs)

	return wrapper


def logout_required(*, otherwise_redirect: str = "accounts.profile") -> Callable:
	def decorator(f: Callable) -> Callable:
		return _make_condition_decorator(
			f, lambda: not current_user.is_authenticated,
			lambda: redirect(url_for(otherwise_redirect)),
			return_otherwise=True,
		)
	return decorator


def staff_required(f: Callable) -> Callable:
	return _make_condition_decorator(f, lambda: current_user.is_staff, lambda: abort(404))


def password_available_required(f: Callable) -> Callable:
	return _make_condition_decorator(
		f, lambda: current_user.password_hash is not None,
		lambda: redirect(url_for("accounts.set_password")),
		return_otherwise=True,
	)


def password_unavailable_required(f: Callable) -> Callable:
	return _make_condition_decorator(f, lambda: current_user.password_hash is None,
 									lambda: abort(403))


def session_item_required(name: str, /) -> Callable:
	def decorator(f: Callable) -> Callable:
		@wraps(f)
		def wrapper(*args: Any, **kwargs: Any) -> Any:
			item = session.get(name)
			if item is None:
				abort(403)
			return f(item, *args, **kwargs)

		return wrapper

	return decorator


def totp_enabled_required(f: Callable) -> Callable:
	return _make_condition_decorator(f, lambda: current_user.totp_is_enabled, lambda: abort(403))


def totp_disabled_required(f: Callable) -> Callable:
	return _make_condition_decorator(f, lambda: not current_user.totp_is_enabled,
 									lambda: abort(403))


def email_confirmed_required(f: Callable) -> Callable:
	return _make_condition_decorator(
		f, lambda: current_user.email_is_confirmed,
		lambda: redirect(url_for("accounts.confirm_email")),
		return_otherwise=True,
	)


def email_unconfirmed_required(f: Callable) -> Callable:
	return _make_condition_decorator(
		f, lambda: not current_user.email_is_confirmed,
		lambda: redirect(url_for("accounts.confirm_email_done")),
		return_otherwise=True,
	)


def password_confirm_once_required(f: Callable) -> Callable:
	"""Before adding this decorator, make sure that your
	route allows the processing of `POST` requests."""

	def condition() -> bool:
		return (current_user.password_hash is None
				or session.get("password_was_once_confirmed", False))

	def otherwise():
		if request.method == "POST":
			bound_form = PasswordForm(request.form)
			if bound_form.validate_on_submit():
				session['password_was_once_confirmed'] = True
				return redirect(request.url)
			return render_template("accounts/password/confirm.html", form=bound_form)
		return render_template("accounts/password/confirm.html", form=PasswordForm())

	return _make_condition_decorator(f, condition, otherwise, return_otherwise=True)


_login_required_above_required_doc = """
Before using this decorator, make sure that `flask_login.login_required`
is above in the decorators "tower". This is necessary because this
decorator works only with users who are logged in to their account.
"""

for decorator in (
	staff_required,
	totp_enabled_required,
	totp_disabled_required,
	email_confirmed_required,
	email_unconfirmed_required,
	password_available_required,
	password_unavailable_required,
	password_confirm_once_required,
):
	if decorator.__doc__ is None:
		decorator.__doc__ = ""
	decorator.__doc__ += "\n" + _login_required_above_required_doc


# Circular imports
from .accounts.forms import PasswordForm
