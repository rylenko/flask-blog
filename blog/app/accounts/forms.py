from typing import Any, Optional

from flask_babel import _
from flask_babel import lazy_gettext as _l
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, TextAreaField, validators

from .. import db
from ..models import User
from .. import fields as common
from ..utils import _make_avoiding_condition


class LoginForm(FlaskForm):
	email = common.EmailField()
	password = common.PasswordField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-primary",
		'value': _l("Log in"),
	})

	requested_user: Optional[User] = None

	def validate_on_submit(self) -> bool:
		self.requested_user = User.query.filter_by(email=self.email.data, is_active=True).first()
		return super().validate_on_submit()

	def validate_submit(self, field: common.SubmitField) -> None:
		if not (
			self.requested_user is not None
			and self.requested_user.check_password(self.password.data)
		):
			raise validators.ValidationError(_("Invalid email or password."))


class RegisterForm(FlaskForm):
	email = common.EmailField()
	username = common.UsernameField()
	password = common.PasswordField()
	password_confirm = common.PasswordConfirmField()
	recaptcha = common.RecaptchaField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-success",
		'value': _l("Register"),
	})

	def populate(self) -> User:
		rv = User(email=self.email.data, username=self.username.data)
		rv.set_password(self.password.data)
		db.session.add(rv)

		return rv

	def validate_email(self, field: common.EmailField) -> None:
		if User.query.filter_by(email=field.data).first() is not None:
			raise validators.ValidationError(_("A user with this email already exists."))

	def validate_username(self, field: common.UsernameField) -> None:
		if User.query.filter_by(username=field.data).first() is not None:
			raise validators.ValidationError(_("A user with this name already exists."))


class TOTPForm(FlaskForm):
	min_length = 6
	max_length = 6

	totp = StringField(
		label=_l("TOTP"),
		validators=(
			validators.DataRequired(message=_l("TOTP field is required.")),
			validators.Length(min=min_length, max=max_length, message=_l(
				"TOTP length must not be more or less than %(max)d characters."
			)),
		),
		render_kw={
			'minlength': min_length, 'maxlength': max_length,
			'class': "form-control", 'placeholder': _l("Enter current TOTP..."),
		},
	)
	sumbit = common.SubmitField()

	def __init__(self, *args: Any, user: Optional[User] = None, **kwargs: Any) -> None:
		self.user = user or current_user
		super().__init__(*args, **kwargs)

	def validate_totp(self, field: StringField) -> None:
		if not self.user.check_current_totp(field.data):
			raise validators.ValidationError(_("Invalid current TOTP."))


class BackupCodeForm(FlaskForm):
	min_length = 8
	max_length = 8

	backup_code = StringField(
		label=_l("Backup code"),
		validators=(
			validators.DataRequired(message=_l("Backup code field is required.")),
			validators.Length(min=min_length, max=max_length, message=_l(
				"Backup code length must not be more or less than %(max)d characters.",
			)),
		),
		render_kw={
			'class': "form-control",
			'minlength': min_length, 'maxlength': max_length,
			'placeholder': _l("Enter one of your backup codes..."),
		},
	)
	submit = common.SubmitField()

	def __init__(self, *args: Any, user: Optional[User] = None, **kwargs: Any) -> None:
		self.user = user or current_user
		super().__init__(*args, **kwargs)

	def validate_backup_code(self, field: StringField) -> None:
		if not self.user.check_backup_code(field.data):
			raise validators.ValidationError(_("Invalid backup code."))


class UpdateForm(FlaskForm):
	information_max_length = 300
	location_max_length = 45

	image = common.ImageField()
	email = common.EmailField()
	username = common.UsernameField()
	information = TextAreaField(
		label=_l("Information"),
		validators=(validators.Length(max=information_max_length, message=_l(
			"Information length must not be more than %(max)d characters."
		)),),
		render_kw={'class': 'form-control', 'maxlength': information_max_length,
   				'placeholder': _l("Enter your information...")},
	)
	location = StringField(
		label=_l("Location"),
		validators=(validators.Length(max=location_max_length, message=_l(
			"Location length must not be more than %(max)d characters."
		)),),
		render_kw={'class': "form-control", 'maxlength': location_max_length,
   				'placeholder': _l("Enter your location...")},
	)
	is_receiving_notifications = BooleanField(label=_l("Receive notifications"))
	recaptcha = common.RecaptchaField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-primary",
		'value': _l("Update"),
	})

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		self._avoiding_condition = _make_avoiding_condition(current_user._get_current_object())

		super().__init__(*args, **kwargs)

		if current_user.is_receiving_notifications:
			self.is_receiving_notifications.default = "checked"

	def populate(self) -> None:
		if self.image.data is not None:
			current_user.set_image(self.image.data)
		self.populate_obj(current_user)

	def validate_email(self, field: common.EmailField) -> None:
		unique_conditions = (User.email == field.data, self._avoiding_condition)

		if User.query.filter(*unique_conditions).first() is not None:
			raise validators.ValidationError(_("A user with this email already exists."))

	def validate_username(self, field: common.UsernameField) -> None:
		unique_conditions = (User.username == field.data, self._avoiding_condition)

		if User.query.filter(*unique_conditions).first() is not None:
			raise validators.ValidationError(_("A user with this name already exists."))


class PasswordForm(FlaskForm):
	password = common.PasswordField()
	sumbit = common.SubmitField()

	def validate_password(self, field: common.PasswordField) -> None:
		if not current_user.check_password(field.data):
			raise validators.ValidationError(_("Wrong password."))


class PasswordSetForm(FlaskForm):
	new_password = common.NewPasswordField()
	new_password_confirm = common.NewPasswordConfirmField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-success",
		'value': _l("Set"),
	})


class PasswordChangeForm(PasswordSetForm):
	old_password = common.OldPasswordField()
	recaptcha = common.RecaptchaField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-primary",
		'value': _l("Change"),
	})

	def validate_new_password(self, field: common.NewPasswordField) -> None:
		if current_user.check_password(field.data):
			raise validators.ValidationError(_("You cannot set the same password."))


class DeactivateForm(FlaskForm):
	password = common.PasswordField()
	recaptcha = common.RecaptchaField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-danger",
		'value': _l("Deactivate"),
	})

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)

		if current_user.password_hash is None:
			del self.password

	def validate_password(self, field: common.PasswordField) -> None:
		if not current_user.check_password(field.data):
			raise validators.ValidationError(_("Wrong password."))


class EmailConfirmForm(FlaskForm):
	submit = common.SubmitField(render_kw={
		'class': "btn btn-success btn-lg btn-block",
		'value': _l("Confirm"),
	})

	def validate_submit(self, field: common.SubmitField) -> None:
		if current_user.has_active_mail_token:
			raise validators.ValidationError(_(
				"You have recently used mail tokens. Wait"
				" a little while until they are removed."
			))


class PasswordResetForm(FlaskForm):
	email = common.EmailField()
	recaptcha = common.RecaptchaField()
	submit = common.SubmitField(render_kw={
		'class': "btn btn-primary",
		'value': _l("Send mail"),
	})

	def validate_on_submit(self) -> bool:
		self.requested_user = User.query.filter_by(email=self.email.data, is_active=True).first()
		return super().validate_on_submit()

	def validate_email(self, field: common.EmailField) -> None:
		if self.requested_user is None:
			raise validators.ValidationError(_(
				"A user with such email does not exist.",
			))
		elif self.requested_user.password_hash is None:
			raise validators.ValidationError(_(
				"You do not have a password, just log in through OAuth.",
			))
		elif self.requested_user.has_active_mail_token:
			raise validators.ValidationError(_(
				"You have recently used mail tokens."
				" Wait a little while until they are removed."
			))
