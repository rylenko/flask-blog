from io import BytesIO

from flask import (
	abort,
	flash,
	url_for,
	request,
	jsonify,
	session,
	redirect,
	current_app,
	render_template,
)
from flask_babel import _
from flask_login import login_user, logout_user, current_user, login_required
from flask_dance.consumer.base import BaseOAuthConsumerBlueprint
from werkzeug.datastructures import CombinedMultiDict

from . import oauth, accounts_bp
from .forms import (
	TOTPForm,
	LoginForm,
	UpdateForm,
	RegisterForm,
	PasswordForm,
	DeactivateForm,
	BackupCodeForm,
	PasswordSetForm,
	EmailConfirmForm,
	PasswordResetForm,
	PasswordChangeForm,
)
from .tasks import (
	send_email_confirm_mail_task,
	send_password_reset_mail_task,
	send_register_success_mail_task,
	send_deactivate_success_mail_task,
	send_totp_enable_success_mail_task,
	send_totp_disable_success_mail_task,
	send_password_set_success_mail_task,
	send_email_confirm_success_mail_task,
	send_backup_codes_are_empty_mail_task,
	send_password_reset_success_mail_task,
	send_password_change_success_mail_task,
)
from .. import db
from ..decorators import (
	logout_required,
	session_item_required,
	totp_enabled_required,
	totp_disabled_required,
	email_confirmed_required,
	email_unconfirmed_required,
	password_available_required,
	password_unavailable_required,
	password_confirm_once_required,
)
from ..utils import login as _login
from ..utils import paginate, get_next_url
from ..types import LoginTwoFactorTypedDict
from ..models import User, Session, PostLike, MailToken, PostComment, Notification


@accounts_bp.get("/profile/")
@login_required
def profile():
	return render_template("accounts/profile.html")


@accounts_bp.get("/notifications/")
@login_required
def notifications():
	qs = current_user.notifications.order_by(Notification.created_at.desc())
	current_page = qs.paginate(per_page=current_app.config['NOTIFICATIONS_PER_PAGE'])

	return render_template("accounts/notifications.html", page=current_page)


@accounts_bp.get("/notifications/count/")
@login_required
def notifications_count():
	qs = current_user.notifications
	all_count = qs.count()
	not_checked_count = qs.filter_by(is_checked=False).count()

	return jsonify(all=all_count, not_checked=not_checked_count)


@accounts_bp.post("/notifications/<int:id>/check/")
@login_required
def check_notification(id: int):
	notification = current_user.notifications.filter_by(id=id).first_or_404()
	notification.is_checked = True
	db.session.commit()

	return redirect(url_for("accounts.notifications"))


@accounts_bp.post("/notifications/delete-all/")
@login_required
def delete_notifications():
	current_user.notifications.delete()
	db.session.commit()

	flash(_("All notifications were successfully deleted."), "danger")
	return redirect(url_for("accounts.notifications"))


@accounts_bp.get("/action-logs/")
@login_required
def action_logs():
	logs = list(current_user.action_logs.items())
	current_page = paginate(logs, per_page=current_app.config['ACTION_LOGS_PER_PAGE'])
	return render_template("accounts/action-logs.html", page=current_page)


@accounts_bp.get("/posts/likes/")
@login_required
def post_likes():
	qs = current_user.post_likes.order_by(PostLike.created_at.desc())
	current_page = qs.paginate(per_page=current_app.config['POST_LIKES_PER_PAGE'])

	return render_template("accounts/posts/likes.html", page=current_page)


@accounts_bp.get("/posts/comments/")
@login_required
def post_comments():
	qs = current_user.post_comments.order_by(PostComment.created_at.desc())
	current_page = qs.paginate(per_page=current_app.config['POST_COMMENTS_PER_PAGE'])

	return render_template("accounts/posts/comments.html", page=current_page)


@accounts_bp.route("/login/", methods=("GET", "POST"))
@logout_required()
def login():
	if request.method == "POST":
		bound_form = LoginForm(request.form)

		if bound_form.validate_on_submit():
			requested_user = bound_form.requested_user
			next_url = get_next_url()

			if requested_user.totp_is_enabled:  # type: ignore
				two_factor: LoginTwoFactorTypedDict = {
					'user_id': requested_user.id,  # type: ignore
					'next_url': next_url,
				}
				session['login_two_factor'] = two_factor
				return redirect(url_for("accounts.login_two_factor"))

			return _login(requested_user, next_url=next_url)  # type: ignore

		if bound_form.requested_user is not None:
			bound_form.requested_user.log_action("Failed login to account.")
		return render_template("accounts/login/index.html", form=bound_form)

	return render_template("accounts/login/index.html", form=LoginForm())


@accounts_bp.route("/login/two-factor/", methods=("GET", "POST"))
@logout_required()
@session_item_required("login_two_factor")
def login_two_factor(item: LoginTwoFactorTypedDict):
	template_name = "accounts/login/two-factor/index.html"
	user = User.query.get(item['user_id'])

	if request.method == "POST":
		bound_form = TOTPForm(request.form, user=user)

		if bound_form.validate_on_submit():
			del session['login_two_factor']
			return _login(user, next_url=item['next_url'])

		return render_template(template_name, form=bound_form, user=user)

	return render_template(template_name, form=TOTPForm(), user=user)


@accounts_bp.route("/login/two-factor/backup-code/", methods=("GET", "POST"))
@logout_required()
@session_item_required("login_two_factor")
def login_two_factor_backup_code(item: LoginTwoFactorTypedDict):
	template_name = "accounts/login/two-factor/backup-code.html"
	user = User.query.get(item['user_id'])

	if not user.backup_code_hashes:
		abort(403)

	if request.method == "POST":
		bound_form = BackupCodeForm(request.form, user=user)

		if bound_form.validate_on_submit():
			del session['login_two_factor']
			user.delete_backup_code(bound_form.backup_code.data)
			flash(_("Used backup code was deleted."), "danger")

			if not user.backup_code_hashes:
				flash(_("You spent all your backup codes."), "danger")
				send_backup_codes_are_empty_mail_task.delay(user.id)
			return _login(user, next_url=item['next_url'])

		return render_template(template_name, form=bound_form)

	return render_template(template_name, form=BackupCodeForm())


@accounts_bp.route("/register/", methods=("GET", "POST"))
@logout_required()
def register():
	if request.method == "POST":
		bound_form = RegisterForm(request.form)

		if bound_form.validate_on_submit():
			new_user = bound_form.populate()
			db.session.commit()

			new_user.log_action("Registered.")
			send_register_success_mail_task.delay(new_user.id)
			flash(_("You have successfully registered your account."), "success")

			login_user(new_user)
			return redirect(url_for("accounts.confirm_email"))

		return render_template("accounts/register.html", form=bound_form)

	return render_template("accounts/register.html", form=RegisterForm())


@accounts_bp.get("/sessions/")
@login_required
def sessions():
	objects = current_user.sessions.order_by(Session.last_online.desc()).all()
	return render_template("accounts/sessions.html", objects=objects)


@accounts_bp.post("/sessions/<int:id>/terminate/")
@login_required
def terminate_session(id: int):
	obj = current_user.sessions.filter_by(id=id).first_or_404()
	if obj.key == session.key:  # type: ignore
		# We can't terminate a current session
		abort(404)
	db.session.delete(obj)
	db.session.commit()

	return redirect(url_for("accounts.sessions"))


@accounts_bp.get("/oauths/")
@login_required
def oauths():
	blueprints = tuple(b for b in current_app.blueprints.values()
   					if isinstance(b, BaseOAuthConsumerBlueprint))
	return render_template("accounts/oauths.html", oauth_blueprints=blueprints)


@accounts_bp.get("/oauths/github/")
def oauths_github():
	bp = oauth.accounts_github_bp

	if bp.session.authorized:
		# Skip OAuth token request and start the main mechanism
		return oauth.github_handler(bp, token=bp.session.token)
	return redirect(url_for("github.login"))


@accounts_bp.post("/oauths/<provider>/unbind/")
@login_required
def unbind_oauth(provider: str):
	bind = current_user.oauths.filter_by(provider=provider).first_or_404()

	if current_user.password_hash is None and current_user.oauths.count() == 1:
		flash(_("By removing the last OAuth bind, you will no longer be able"
				" to log in to your account, as you have no password set."), "danger")
	else:
		db.session.delete(bind)
		db.session.commit()
		current_user.log_action("Unbind his %s account." % provider)
		flash(_("Your %(oauth)s was successfully unbinded.", oauth=provider), "success")

	return redirect(url_for("accounts.oauths"))


@accounts_bp.get("/logout/")
@login_required
def logout():
	current_user.log_action("Logged out.")
	flash(_("You have successfully logged out of your account."), "success")
	logout_user()

	return redirect(url_for("main.index"))


@accounts_bp.route("/password/set/", methods=("GET", "POST"))
@login_required
@password_unavailable_required
def set_password():
	"""May be useful when a user has just registered
	based on `OAuth` data and has not yet set a password."""

	if request.method == "POST":
		bound_form = PasswordSetForm(request.form)

		if bound_form.validate_on_submit():
			current_user.set_password(bound_form.new_password.data)
			db.session.commit()

			current_user.log_action("Set password for the first time.")
			send_password_set_success_mail_task.delay(current_user.id)
			flash(_("Your password has been successfully set."), "success")

			return redirect(url_for("accounts.profile"))

		return render_template("accounts/password/set.html", form=bound_form)

	return render_template("accounts/password/set.html", form=PasswordSetForm())


@accounts_bp.route("/password/change/", methods=("GET", "POST"))
@login_required
@password_available_required
def change_password():
	if request.method == "POST":
		bound_form = PasswordChangeForm(request.form)

		if bound_form.validate_on_submit():
			current_user.set_password(bound_form.new_password.data)
			db.session.commit()

			current_user.log_action("Changed his password.")
			send_password_change_success_mail_task.delay(current_user.id)
			flash(_("Your password has been successfully changed."), "success")

			return redirect(url_for("accounts.profile"))

		return render_template("accounts/password/change.html", form=bound_form)

	return render_template("accounts/password/change.html", form=PasswordChangeForm())


@accounts_bp.route("/update/", methods=("GET", "POST"))
@login_required
@password_confirm_once_required
def update():
	if request.method == "POST":
		form_and_files = CombinedMultiDict((request.form, request.files))
		bound_form = UpdateForm(form_and_files)

		if bound_form.validate_on_submit():
			bound_form.populate()
			db.session.commit()

			current_user.log_action("Updated his profile.")
			flash(_("Your account was updated successfully."), "success")

			return redirect(url_for("accounts.profile"))

		return render_template("accounts/update.html", form=bound_form)

	return render_template("accounts/update.html", form=UpdateForm(obj=current_user))


@accounts_bp.route("/deactivate/", methods=("GET", "POST"))
@login_required
def deactivate():
	if request.method == "POST":
		bound_form = DeactivateForm(request.form)

		if bound_form.validate_on_submit():
			current_user.is_active = False
			db.session.commit()

			current_user.log_action("Deactivated his profile.")
			send_deactivate_success_mail_task.delay(current_user.id)
			flash(_("You have successfully deactivated your account."), "danger")

			logout_user()
			return redirect(url_for("main.index"))

		return render_template("accounts/deactivate.html", form=bound_form)

	return render_template("accounts/deactivate.html", form=DeactivateForm())


@accounts_bp.get("/totp/qrcode/")
@login_required
@totp_disabled_required
def totp_qrcode():
	qrcode_io = BytesIO()
	qrcode = current_user.get_totp_qrcode()
	qrcode.svg(qrcode_io, scale=5)

	return qrcode_io.getvalue(), 200, {'Content-Type': "image/svg+xml"}


@accounts_bp.route("/totp/enable/", methods=("GET", "POST"))
@login_required
@totp_disabled_required
@password_confirm_once_required
def enable_totp():
	if request.method == "POST":
		bound_form = TOTPForm(request.form)

		if bound_form.validate_on_submit():
			current_user.totp_is_enabled = True
			db.session.commit()

			current_user.log_action("Enabled TOTP.")
			flash(_("You successfully enabled TOTP."), "success")
			send_totp_enable_success_mail_task.delay(current_user.id)

			return redirect(url_for("accounts.backup_codes"))

		return render_template("accounts/totp/enable.html", form=bound_form)

	return render_template("accounts/totp/enable.html", form=TOTPForm())


@accounts_bp.route("/totp/disable/", methods=("GET", "POST"))
@login_required
@password_available_required
@totp_enabled_required
def disable_totp():
	if request.method == "POST":
		bound_form = PasswordForm(request.form)

		if bound_form.validate_on_submit():
			current_user.totp_is_enabled = False
			db.session.commit()

			current_user.log_action("Disabled TOTP.")
			flash(_("You successfully disabled TOTP."), "danger")
			send_totp_disable_success_mail_task.delay(current_user.id)

			return redirect(url_for("accounts.profile"))

		return render_template("accounts/totp/disable.html", form=bound_form)

	return render_template("accounts/totp/disable.html", form=PasswordForm())


@accounts_bp.route("/backup-codes/", methods=("GET", "POST"))
@login_required
@totp_enabled_required
@password_confirm_once_required
def backup_codes():
	if request.method == "POST":
		new_codes = current_user.genset_backup_codes()
		db.session.commit()

		current_user.log_action("Generated new backup codes.")
		flash(_("Backup codes were successfully generated."), "success")

		return render_template("accounts/backup-codes.html", codes=new_codes)

	return render_template("accounts/backup-codes.html")


@accounts_bp.route("/email/confirm/", methods=("GET", "POST"))
@login_required
@email_unconfirmed_required
def confirm_email():
	if request.method == "POST":
		bound_form = EmailConfirmForm(request.form)

		if bound_form.validate_on_submit():
			current_user.log_action("Requested a mail to confirm the email.")
			send_email_confirm_mail_task.delay(current_user.id)
			flash(_("A confirmation mail has been sent."), "success")

		return render_template("accounts/email/confirm.html", form=bound_form)

	return render_template("accounts/email/confirm.html", form=EmailConfirmForm())


@accounts_bp.get("/email/confirm/act/<mail_token_key>/")
@login_required
@email_unconfirmed_required
def confirm_email_act(mail_token_key: str):
	mail_token = MailToken.query.filter_by(
		key=mail_token_key, owner=current_user,
		type=MailToken.EMAIL_CONFIRM_TYPE,
	).first()

	if mail_token is None:
		abort(404)

	current_user.email_is_confirmed = True
	db.session.delete(mail_token)

	db.session.commit()
	current_user.log_action("Has confirmed his email.")
	send_email_confirm_success_mail_task.delay(current_user.id)

	return redirect(url_for("accounts.confirm_email_done"))


@accounts_bp.get("/email/confirm/done/")
@login_required
@email_confirmed_required
def confirm_email_done():
	return render_template("accounts/email/confirm-done.html")


@accounts_bp.route("/password/reset/", methods=("GET", "POST"))
@logout_required(otherwise_redirect="accounts.change_password")
def reset_password():
	if request.method == "POST":
		bound_form = PasswordResetForm(request.form)

		if bound_form.validate_on_submit():
			requested_user = bound_form.requested_user

			send_password_reset_mail_task.delay(requested_user.id)
			requested_user.log_action("Requested a mail to reset the password.")
			flash(_("A reset password mail has been sent."), "success")

		return render_template("accounts/password/reset.html", form=bound_form)

	return render_template("accounts/password/reset.html", form=PasswordResetForm())


@accounts_bp.route("/password/reset/act/<mail_token_key>/", methods=("GET", "POST"))
@logout_required(otherwise_redirect="accounts.change_password")
def reset_password_act(mail_token_key: str):
	mail_token = MailToken.query.filter_by(type=MailToken.PASSWORD_RESET_TYPE,
   										key=mail_token_key).first()
	if mail_token is None:
		abort(404)

	if request.method == "POST":
		bound_form = PasswordSetForm(request.form)

		if bound_form.validate_on_submit():
			mail_token.owner.set_password(bound_form.new_password.data)

			mail_token.owner.log_action("Reset password.")
			send_password_reset_success_mail_task.delay(mail_token.owner.id)
			flash(_("Your password has been successfully reset."), "success")
			db.session.delete(mail_token)

			db.session.commit()
			return render_template("accounts/password/reset-done.html")

		return render_template("accounts/password/set.html", form=bound_form)

	return render_template("accounts/password/set.html", form=PasswordSetForm())
