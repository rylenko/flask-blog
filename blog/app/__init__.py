import os
import logging
from typing import Type, Optional

import redis
import sentry_sdk
from flask import Flask, request, current_app
from flask_mail import Mail
from flask_admin import Admin
from flask_babel import Babel
from flask_babel import lazy_gettext as _l
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from sentry_sdk.integrations.flask import FlaskIntegration

from .config import BaseConfig, ProductionConfig
from .initializers import (
	register_blueprints,
	register_cli_groups,
	add_jinja_extensions,
	register_jinja_filters,
	add_logging_file_handler,
	add_logging_smtp_handler,
	register_admin_panel_views,
	register_context_processor,
	register_shell_context_processor,
)


# Packages announcement
mail = Mail()
babel = Babel()
db = SQLAlchemy()
csrf = CSRFProtect()
login_manager = LoginManager()
migrate = Migrate(db=db, directory=BaseConfig.MIGRATIONS_DIR)

# The tuple of components that will be automatically
# initialized with `component(app)` through a loop in `create_app`
automatically_init_components = (
	db.init_app,
	csrf.init_app,
	mail.init_app,
	babel.init_app,
	migrate.init_app,
	login_manager.init_app,
	register_blueprints,
	register_cli_groups,
	add_jinja_extensions,
	register_jinja_filters,
	register_context_processor,
	register_shell_context_processor,
)


def create_app(config: Type[BaseConfig] = ProductionConfig) -> Flask:
	app = Flask(__name__)
	app.config.from_object(config)
	app.wsgi_app = ProxyFix(app.wsgi_app)  # type: ignore
	app.logger.setLevel(logging.INFO)
	app.session_interface = DatabaseSessionInterface()  # type: ignore

	for component in automatically_init_components:
		component(app)

	if not app.debug and not app.testing:
		sentry_dsn = app.config['SENTRY_DSN']

		app.action_logger = redis.from_url(  # type: ignore
			app.config['ACTION_LOGS_STORAGE_URL'],
			decode_responses=True
		)
		add_logging_file_handler(app)

		if sentry_dsn is None:
			add_logging_smtp_handler(app)
		else:
			sentry_sdk.init(
				dsn=sentry_dsn,
				traces_sample_rate=1.0,
				integrations=[FlaskIntegration()],
			)

	# When i try to take it outside. i always get errors :(
	admin = Admin(app, index_view=AdminIndexView(name="Admin"))
	register_admin_panel_views(admin)

	# Configuring OAuth
	if app.config['SERVER_NAME'].startswith("localhost"):
		# This option allows you to use the oauthlib without HTTPS
		os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = "1"

	return app


# Configuring Login Manager
from .models import User

login_manager.login_view = "accounts.login"
login_manager.login_message = _l("Please log in to access this page.")


@login_manager.user_loader
def load_user(id: int) -> Optional[User]:
	return User.query.get(id)


# Configuring Babel
@babel.localeselector
def get_locale() -> Optional[str]:
	best_match = request.accept_languages.best_match
	return best_match(current_app.config['LANGUAGES'])


# Circular imports
from .admin_panel import AdminIndexView
from .session import DatabaseSessionInterface
