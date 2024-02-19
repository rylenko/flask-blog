import secrets
from time import time
from io import BytesIO
from typing import Union, Optional
from collections.abc import Sequence
from urllib.parse import urljoin, urlparse

import bleach
from flask import abort, flash, url_for, request, redirect, current_app
from flask_babel import _
from flask_wtf import FlaskForm
from flask_login import login_user, current_user
from flask_sqlalchemy import Pagination
from werkzeug.wrappers import Response
from werkzeug.datastructures import FileStorage
from sqlalchemy.sql.expression import BinaryExpression
from PIL import Image
from PIL.Image import Image as PillowImage
from markdown import markdown
from slugify import slugify

from .models import User, BaseModel


def generate_slug(base: str, /) -> str:
	new_slug = slugify(base)
	now = str(int(time()))

	return new_slug + "-" + now


def delete_image(filename: str, /) -> None:
	current_app.config['IMAGES_DIR'].joinpath(filename).unlink()


def save_image(image: Union[FileStorage, BytesIO], /) -> str:
	"""Generates a filename for the image and saves the image below it.
	If the size of the transferred image was larger than `IMAGES_MAX_SIZE`,
	then it will be equated to it.

	:return: Generated filename
	"""

	dir_ = current_app.config['IMAGES_DIR']
	max_size = current_app.config['IMAGES_MAX_SIZE']

	while True:
		# Generate unique save path for image
		filename = secrets.token_hex(16) + ".jpg"
		save_path = dir_.joinpath(filename)
		if not save_path.exists():
			break

	with Image.open(image) as new_image:  # type: ignore
		# Small important corrections and saving
		if new_image.mode != "RGB":
			new_image = new_image.convert("RGB")
		new_image.thumbnail(max_size, Image.LANCZOS)
		new_image.save(save_path, optimize=True, quality=95)

	return filename


def save_image_in_memory(image: PillowImage, /, format_: str) -> BytesIO:
	"""It is usually used when we need to take an image, change
	it using `Pillow` and quickly save the result for future use,
	as a new image object."""

	image_io = BytesIO()
	image.save(image_io, format_, optimize=True, quality=95)
	image_io.seek(0)

	return image_io


def get_image_url(**options: Union[str, int]) -> str:
	"""Example: `get_image_url(filename="my-icon.jpg", size=512)`"""
	return url_for("main.image", **options)


def is_safe_url(url: str, /) -> bool:
	host_url = urlparse(request.host_url)
	target_url = urlparse(urljoin(request.host_url, url))

	return (target_url.scheme in {"http", "https"}
			and target_url.netloc == host_url.netloc)


def get_next_url() -> Optional[str]:
	"""Used to retrieve the link from `?next`, to which the user
	should be redirected when the view has finished its work."""

	rv = request.args.get("next", type=str)
	return rv if rv is not None and is_safe_url(rv) else None


def login(user: User, next_url: Optional[str]) -> Response:
	"""Use this when the validation of the data entered by
	the user is successful and you can skip his to account."""

	login_user(user)

	user.log_action("Logged in.")
	flash(_("You have successfully logged into your account."), "success")

	if not user.email_is_confirmed:
		return redirect(url_for("accounts.confirm_email"))
	return redirect(next_url or url_for("accounts.profile"))


def paginate(elements: Sequence, /, per_page: int) -> Pagination:
	"""Same `flask_sqlalchemy.BaseQuery.paginate`,
	but suitable for regular sequences."""

	current_page: int = request.args.get("page", 1, type=int)  # type: ignore
	if current_page <= 0:
		abort(404)

	offset = (current_page - 1) * per_page
	rv = elements[offset:offset + per_page]

	# `current_page > 1`, to display a message on
	# the first page that we do not have any items
	if not rv and current_page > 1:
		abort(404)

	return Pagination(None, current_page, per_page, len(elements), rv)


def _make_avoiding_condition(obj: BaseModel, /) -> BinaryExpression:
	"""When checking the uniqueness of the new data of an `obj_on_update` in
	the form (through `Model.query.filter(Model.unique_field == new_data`),
	we can get `obj_on_update` if the data remained unchanged. This condition
	helps us avoid it."""
	return obj.__class__.id != obj.id


def process_user_markdown(text: str, /) -> str:
	"""This function turns the user-supplied `markdown` into `HTML`,
	and then deletes the tags that are prohibited for users from the `HTML`.
	It is mandatory to use, for example, before saving the text of a comment."""

	html = markdown(text, output_format="html")
	allowed_tags = current_app.config['USER_ALLOWED_HTML_TAGS']

	return bleach.linkify(bleach.clean(html, tags=allowed_tags, strip=True))


def flash_form_errors(form: FlaskForm, /) -> None:
	for field_errors in form.errors.values():
		for error in field_errors:
			flash(error, "danger")


def check_rights_on_object(obj: BaseModel, /, *, owner_field_name: str = "author") -> bool:
	"""Checks whether the current user has the right to modify the object.

	:param owner_field_name: The field of the `obj`, where
		stored the user, who is responsible for creating the object.
	"""

	if not current_user.is_authenticated:
		return False
	elif current_user.is_staff:
		return True
	return getattr(obj, owner_field_name) == current_user


def get_user_agent() -> str:
	params = {name: getattr(request.user_agent, name) or "undefined"
  			for name in ("browser", "platform", "language", "version")}
	return current_app.config['USER_AGENT_FORMAT'].format(**params)
