from flask import url_for, render_template
from flask_mail import Message

from .. import db, mail
from ..models import User, MailToken
from ..celery_ import make_celery


celery = make_celery()


@celery.task
def send_register_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)
	email_confirm_url = url_for("accounts.confirm_email")

	subject = "You have successfully registered on Flask-Blog!"
	text = render_template("accounts/mails/register-done.html",
   						username=user.username, email_confirm_url=email_confirm_url)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_password_set_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "For the first time, your account has a password on Flask-Blog."
	text = render_template("accounts/mails/password/set-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_password_change_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "Your password has been successfully changed on Flask-Blog."
	text = render_template("accounts/mails/password/change-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_deactivate_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "Your account has been successfully deactivated on Flask-Blog."
	text = render_template("accounts/mails/deactivate-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_totp_enable_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "You successfully enabled TOTP on Flask-Blog."
	text = render_template("accounts/mails/totp/enable-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_totp_disable_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "You successfully disabled TOTP on Flask-Blog."
	text = render_template("accounts/mails/totp/disable-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_backup_codes_are_empty_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)
	generate_url = url_for("accounts.backup_codes")

	subject = "Your backup codes have just run out on Flask-Blog."
	text = render_template("accounts/mails/backup-codes-empty.html",
   						username=user.username, generate_url=generate_url)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_email_confirm_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)
	new_token = user.create_active_mail_token(MailToken.EMAIL_CONFIRM_TYPE)
	db.session.commit()
	act_url = url_for("accounts.confirm_email_act", mail_token_key=new_token.key)

	subject = "Flask-Blog Email Confirmation."
	text = render_template("accounts/mails/email/confirm.html",
   						username=user.username, act_url=act_url)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_email_confirm_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "Your email has been successfully confirmed on Flask-Blog."
	text = render_template("accounts/mails/email/confirm-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_password_reset_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)
	new_token = user.create_active_mail_token(MailToken.PASSWORD_RESET_TYPE)
	db.session.commit()
	act_url = url_for("accounts.reset_password_act", mail_token_key=new_token.key)

	subject = "Password reset on Flask-Blog"
	text = render_template("accounts/mails/password/reset.html",
   						username=user.username, act_url=act_url)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)


@celery.task
def send_password_reset_success_mail_task(user_id: int) -> None:
	user = User.query.get(user_id)

	subject = "Your password has been successfully reset on Flask-Blog."
	text = render_template("accounts/mails/password/reset-done.html", username=user.username)

	message = Message(subject=subject, html=text, recipients=[user.email])
	mail.send(message)
