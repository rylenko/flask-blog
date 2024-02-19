from typing import Any, Dict, Mapping, Iterable, MutableMapping, TypeAlias

from flask import abort, flash, session, url_for, redirect, current_app
from flask_babel import _
from flask_login import login_user, current_user, login_required
from flask_dance.consumer import oauth_authorized, OAuth2ConsumerBlueprint
from flask_dance.contrib.github import make_github_blueprint
from werkzeug.wrappers import Response

from .. import db
from ..decorators import logout_required
from ..models import OAuth, User


# We do not use the "storage" parameter because it differs
# from the behavior intended by the developers of the library.
# We will work with the storage manually
COMMON_BLUEPRINT_PARAMS = {
	'login_url': "/login/",
	'authorized_url': "/authorized/",
}

Token: TypeAlias = Mapping[str, Any]
SocialData: TypeAlias = MutableMapping[str, Any]

accounts_github_bp = make_github_blueprint(**COMMON_BLUEPRINT_PARAMS)


def _get_json(
	url: str,
	/,
	bp: OAuth2ConsumerBlueprint,
	*,
	required_fields: Iterable[str] = (),
) -> Dict[str, Any]:
	"""Used to get JSON information from OAuth API. Example:

		_get_json(
			"/user",
			accounts_github_bp,
			required_fields=("id", "email", "login"),
		)
	"""

	response = bp.session.get(url)
	if not response.ok:
		flash(_("Request to API failed."), "danger")
		abort(403)

	rv = response.json()
	for field in required_fields:
		if not rv.get(field):
			message = _("The API response didn't give your %(field)s.",
						field=field)
			flash(message, "danger")
			abort(403)

	return rv


@login_required
def _bind_to_current_user_handler(
	bp: OAuth2ConsumerBlueprint, token: Token, social_id: str,
) -> Response:
	"""Based on the data received, it tries to find an `OAuth` bind.
	If the bind cannot be found, it creates it for the current user.
	If a bind has been found, an flash-error is displayed to the user."""

	requested_oauth = OAuth.query.filter_by(
		provider=bp.name,
		social_id=social_id,
	).first()

	if requested_oauth is None:
		new_oauth = OAuth(
			social_id=social_id,
			token=token,
			user=current_user,
			provider=bp.name,
		)
		db.session.add(new_oauth)
		db.session.commit()
	elif requested_oauth.user == current_user:
		flash(_("This OAuth bind already applies to your account."), "danger")
		return redirect(url_for("accounts.oauths"))
	else:
		flash(_("This OAuth bind applies to other account."), "danger")
		return redirect(url_for("accounts.oauths"))

	current_user.log_action("Bind his %s account." % bp.name)
	flash(_(
		"You have successfully bind your %(oauth)s account.",
		oauth=bp.name
	), "success")

	return redirect(url_for("accounts.oauths"))


@logout_required()
def _register_or_login_handler(
	bp: OAuth2ConsumerBlueprint, token: Token, social_data: SocialData,
) -> Response:
	"""Based on the data it receives, it tries to find an `OAuth` binding.
	If an `OAuth` bind has been found, it simply logs on to the account of
	the user who owns the bind. If an `OAuth` bind has not been found, it
	creates a new user account based on the `social_data` of the user"""

	social_id = social_data.pop("id")
	social_email = social_data.pop("email")
	social_username = social_data.pop("username")

	requested_oauth = OAuth.query.filter_by(
		provider=bp.name,
		social_id=social_id,
	).first()

	if requested_oauth is None:
		next_url = url_for("accounts.set_password")

		# Checking email for uniqueness before creating a new account
		if User.query.filter_by(email=social_email).first() is not None:
			flash(_(
				"Someone is already registered with that email.",
			), "danger")
			return redirect(url_for("accounts.login"))
		# Checking username for uniqueness before creating a new account
		elif User.query.filter_by(
			username=social_username,
		).first() is not None:
			flash(_(
				"Someone is already registered with that username.",
			), "danger")
			return redirect(url_for("accounts.login"))

		new_user = User(
			email=social_email,
			username=social_username,
			**social_data,
		)
		db.session.add(new_user)

		requested_oauth = OAuth(
			social_id=social_id,
			token=token,
			user=new_user,
			provider=bp.name,
		)
		db.session.add(requested_oauth)

		from .tasks import send_register_success_mail_task
		send_register_success_mail_task.delay(new_user.id)
		new_user.log_action("Registered via %s" % bp.name)
		flash(_("You have successfully registered via %(oauth)s account.",
				oauth=bp.name), "success")
	else:
		# Set the new fetched token
		requested_oauth.token = token

		if not requested_oauth.user.is_active:
			flash(_("Your account has been deactivated."), "danger")
			return redirect(url_for("accounts.login"))
		elif requested_oauth.user.totp_is_enabled:
			session['login_two_factor'] = {
				'user_id': requested_oauth.user.id,
				'next_url': None,
			}
			return redirect(url_for("accounts.login_two_factor"))
		else:
			next_url = url_for("accounts.profile")
			requested_oauth.user.log_action("Logged in via %s." % bp.name)
			flash(_("You have successfully logged in via %(oauth)s account.",
					oauth=bp.name), "success")

	db.session.commit()
	login_user(requested_oauth.user)
	return redirect(next_url)


def oauth_handler(
	bp: OAuth2ConsumerBlueprint, token: Token, social_data: SocialData,
) -> Response:
	"""A primary handler that accepts data already received from `API`, checks
	that you have passed the required social fields and sends all arguments to
	`_bind_to_current_user_handler` if the user is authenticated, else to
	`_register_or_login_handler`."""

	for required_field in current_app.config['OAUTH_RESPONSE_REQUIRED_FIELDS']:
		if required_field not in social_data:
			raise ValueError(
				"You haven't specified %s in social_data." % required_field,
			)

	if current_user.is_authenticated:
		return _bind_to_current_user_handler(
			bp,
			token,
			social_id=social_data['id'],
		)
	return _register_or_login_handler(bp, token, social_data)


@oauth_authorized.connect_via(accounts_github_bp)
def github_handler(bp: OAuth2ConsumerBlueprint, token: Token) -> Response:
	data = _get_json("/user", bp, required_fields=("id", "email", "login"))
	social_data = {
		'id': str(data['id']),
		'email': data['email'],
		'username': data['login'],
		'information': data['bio'],
		'location': data['location'],
	}
	return oauth_handler(bp, token, social_data)
