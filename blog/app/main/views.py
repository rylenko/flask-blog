from datetime import datetime

from PIL import Image
from flask import abort, request, session, send_file, current_app, render_template
from flask_login import current_user

from . import main_bp
from .. import db
from ..utils import save_image_in_memory


@main_bp.before_app_request
def register_last_online() -> None:
	now = datetime.utcnow()
	session_database_object = session.get_database_object()  # type: ignore

	if session_database_object is not None:
		session_database_object.last_online = now
	if current_user.is_authenticated:
		current_user.last_online = now

	db.session.commit()


@main_bp.get("/")
def index():
	return render_template("main/index.html")


@main_bp.get("/media/images/<filename>/")
def image(filename: str):
	required_size = request.args.get("size", type=int)
	image_path = current_app.config['IMAGES_DIR'].joinpath(filename)

	if not image_path.exists():
		abort(404)
	elif required_size is None:
		return send_file(image_path)

	with Image.open(image_path) as image:
		if image.format is None:
			raise RuntimeError("Image's format is `None`.")

		image.thumbnail((required_size, required_size), Image.LANCZOS)
		resized_image_io = save_image_in_memory(image, format_=image.format)

		return send_file(resized_image_io, mimetype="image/" + image.format.lower())
