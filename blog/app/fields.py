from __future__ import annotations

from typing import Any

from PIL import Image
from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from flask_babel import _
from flask_babel import lazy_gettext as _l
from flask_wtf.recaptcha import Recaptcha as RecaptchaRequired
from flask_wtf.recaptcha import RecaptchaField as BaseRecaptchaField
from wtforms import validators, StringField
from wtforms import PasswordField as BasePasswordField
from wtforms import SubmitField as BaseSubmitField

from .config import BaseConfig


def _validate_user_email_is_confirmed(form: FlaskForm, field: ImageField) -> None:
	if field.data is not None and not current_user.email_is_confirmed:
		raise validators.StopValidation(_(
			"You can't do this because your email is not confirmed.",
		))


def _validate_image_has_min_size(form: FlaskForm, field: ImageField) -> None:
	if field.data is not None:
		required_size = current_app.config['IMAGES_MIN_SIZE']
		message_template = _("The image should be at least %(width)d"
 							" pixels wide and %(height)d pixels high.")

		with Image.open(field.data) as uploaded_image:
			if uploaded_image.size < required_size:
				raise validators.StopValidation(message_template % dict(
					width=required_size[0], height=required_size[1],
				))


def _validate_old_password(form: FlaskForm, field: OldPasswordField) -> None:
	if not current_user.check_password(field.data):
		raise validators.StopValidation(_("Invalid old password."))


class ImageField(FileField):
	default_label = _l("Image")

	validators = (
		FileAllowed(BaseConfig.IMAGES_ALLOWED_EXTENSIONS,
					message=_l("Image extension not supported.")),
		_validate_user_email_is_confirmed,
		_validate_image_has_min_size,
	)

	def __init__(self, **kwargs: Any) -> None:
		if not current_user.email_is_confirmed:
			kwargs.setdefault("render_kw", {})['disabled'] = "true"
		kwargs.setdefault("label", self.default_label)

		super().__init__(**kwargs)


class EmailField(StringField):
	min_length = 5
	max_length = 45

	default_label = _l("Email")
	default_render_kw = {
		'type': "email", 'class': "form-control",
		'minlength': min_length, 'maxlength': max_length,
		'placeholder': _l("Enter email of your account..."),
	}

	validators = (
		validators.DataRequired(message=_l("Email field is required.")),
		validators.Email(message=_l("The string entered is not email.")),
		validators.Length(min=min_length, max=max_length, message=_l(
			"Email length must not be less than"
			" %(min)d and more than %(max)d characters."
		)),
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class UsernameField(StringField):
	min_length = 3
	max_length = 30

	default_label = _l("Username")
	default_render_kw = {
		'class': "form-control",
		'minlength': min_length, 'maxlength': max_length,
		'placeholder': _l("Enter username of your account..."),
	}

	validators = (
		validators.DataRequired(message=_l("Username field is required.")),
		validators.Length(min=min_length, max=max_length, message=_l(
			"Username length must not be less than"
			" %(min)d and more than %(max)d characters.",
		)),
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class PasswordField(BasePasswordField):
	min_length = 6
	max_length = 50

	default_label = _l("Password")
	default_render_kw = {
		'class': "form-control",
		'minlength': min_length, 'maxlength': max_length,
		'placeholder': _l("Enter password of your account...")
	}

	validators = (
		validators.DataRequired(message=_l("Password field is required.")),
		validators.Length(min=min_length, max=max_length, message=_l(
			"Password length must not be less than"
			" %(min)d and more than %(max)d characters."
		)),
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class PasswordConfirmField(BasePasswordField):
	default_label = _l("Password confirm")
	default_render_kw = {
		'class': "form-control",
		'placeholder': _l("Confirm your password of account..."),
	}

	validators = (
		validators.DataRequired(message=_l("Password confirm field is required.")),
		validators.EqualTo("password", message=_l("Passwords must match.")),
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class OldPasswordField(BasePasswordField):
	default_label = _l("Old password")
	default_render_kw = {
		'class': "form-control",
		'placeholder': _l("Enter your old password of account..."),
	}

	validators = (
		validators.DataRequired(message=_l("Old password field is required.")),
		_validate_old_password,
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class NewPasswordField(BasePasswordField):
	min_length = 6
	max_length = 50

	default_label = _l("New password")
	default_render_kw = {
		'class': "form-control",
		'minlength': min_length, 'maxlength': max_length,
		'placeholder': _l("Enter new password of your account..."),
	}

	validators = (
		validators.DataRequired(message=_l("New password field is required.")),
		validators.Length(min=min_length, max=max_length, message=_l(
			"New password length must not be less than"
			" %(min)d and more than %(max)d characters."
		)),
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class NewPasswordConfirmField(BasePasswordField):
	default_label = _l("New password confirm")
	default_render_kw = {
		'class': "form-control",
		'placeholder': _l("Confirm your new password of your account..."),
	}

	validators = (
		validators.DataRequired(message=_l("New password confirm field is required.")),
		validators.EqualTo("new_password", message=_l("Passwords must match.")),
	)

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class SubmitField(BaseSubmitField):
	default_label = ""
	default_render_kw = {'class': "btn btn-primary", 'value': _l("Submit")}

	def __init__(self, **kwargs: Any) -> None:
		kwargs.setdefault("label", self.default_label)
		kwargs.setdefault("render_kw", self.default_render_kw)

		super().__init__(**kwargs)


class RecaptchaField(BaseRecaptchaField):
	validators = (RecaptchaRequired(message=_l("Captcha field is required.")),)
