import logging
import logging.handlers
from typing import Dict, Type, Union, Callable

from flask import Flask
from flask_admin import Admin
from flask_sqlalchemy import SQLAlchemy
from humanize import naturaltime
from markdown import markdown


def register_blueprints(app: Flask, /) -> None:
	from .main import main_bp
	from .errors import errors_bp
	from .users import users_bp
	from .tags import tags_bp
	from .posts import posts_bp
	from .accounts import accounts_bp
	from .accounts.oauth import accounts_github_bp

	app.register_blueprint(main_bp)
	app.register_blueprint(errors_bp)
	app.register_blueprint(tags_bp, url_prefix="/tags/")
	app.register_blueprint(users_bp, url_prefix="/users/")
	app.register_blueprint(posts_bp, url_prefix="/posts/")
	app.register_blueprint(accounts_bp, url_prefix="/accounts/")
	app.register_blueprint(accounts_github_bp, url_prefix="/accounts/oauths/github/")


def register_cli_groups(app: Flask) -> None:
	from .cli import register_babel_cli, register_models_cli

	register_babel_cli(app)
	register_models_cli(app)


def add_jinja_extensions(app: Flask, /) -> None:
	app.jinja_env.add_extension("jinja2.ext.loopcontrols")


def register_jinja_filters(app: Flask, /) -> None:
	for f in (markdown,):
		app.jinja_env.filters[f.__name__] = f


def register_admin_panel_views(admin: Admin) -> None:
	from .admin_panel import views

	admin.add_view(views.UserView(category="User"))
	admin.add_view(views.SessionView(category="User"))
	admin.add_view(views.OAuthView(category="User"))
	admin.add_view(views.MailTokenView(category="User"))
	admin.add_view(views.NotificationView(category="User"))
	admin.add_view(views.PostView(category="Post"))
	admin.add_view(views.PostLikeView(category="Post"))
	admin.add_view(views.PostCommentView(category="Post"))
	admin.add_view(views.TagView(category="Tag"))

	if hasattr(admin.app, "action_logger"):
		admin.add_view(views.ActionLogsView(
			admin.app.action_logger, name="Action logs",
			category="User", endpoint="action-logs",
		))


def register_context_processor(app: Flask, /) -> None:
	from .utils import get_image_url
	from .utils import check_rights_on_object

	functions = (get_image_url, check_rights_on_object, naturaltime)

	@app.context_processor
	def make_context() -> Dict[str, Callable]:
		return {f.__name__: f for f in functions}  # type: ignore


def register_shell_context_processor(app: Flask, /) -> None:
	from . import db
	from . import models

	included_models = {m.__name__: m for m in (
		models.User, models.OAuth, models.MailToken,
		models.Notification, models.Post, models.Tag,
		models.PostLike, models.PostComment, models.Session
	)}

	@app.shell_context_processor
	def make_shell_context() -> Dict[
		str, Union[SQLAlchemy, Type[models.BaseModel]]
	]:
		return {'db': db, **included_models}


def add_logging_file_handler(app: Flask, /) -> None:
	dir_ = app.config['LOGS_DIR']
	if not dir_.exists():
		dir_.mkdir()

	file_handler = logging.handlers.RotatingFileHandler(
		dir_.joinpath("blog.log"), maxBytes=10240, backupCount=20,
	)
	file_handler.setFormatter(logging.Formatter(
		"%(asctime)s: %(message)s",
	))
	file_handler.setLevel(logging.INFO)
	app.logger.addHandler(file_handler)


def add_logging_smtp_handler(app: Flask, /) -> None:
	subject = "Flask-Blog Failure"
	toaddrs = app.config['MAIL_USERNAME']
	fromaddr = "no-reply" + app.config['MAIL_SERVER']
	mailhost = (app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
	credentials = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

	smtp_handler = logging.handlers.SMTPHandler(
		mailhost, fromaddr, toaddrs, subject,
		credentials=credentials, secure=None,
	)
	smtp_handler.setLevel(logging.ERROR)
	app.logger.addHandler(smtp_handler)
