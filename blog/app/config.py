import os
import datetime
from pathlib import Path

import dotenv


# Loading .Env variables so that there are no errors when used locally.
_base_dir_parent = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(_base_dir_parent.joinpath(".env"))


def _get_postgresql_database_uri() -> str:
	user = os.environ['POSTGRES_USER']
	password = os.environ['POSTGRES_PASSWORD']
	db = os.environ['POSTGRES_DB']

	return f"postgresql://{user}:{password}@db:5432/{db}"


class BaseConfig:
	DEBUG = True
	SERVER_NAME = "localhost"
	SECRET_KEY = os.environ['SECRET_KEY']

	LANGUAGES = ("en", "ru")
	TOTP_ISSUER_NAME = "Flask-Blog"
	SENTRY_DSN = os.environ.get("SENTRY_DSN")
	OAUTH_RESPONSE_REQUIRED_FIELDS = {"id", "email", "username"}
	SQLALCHEMY_TRACK_MODIFICATIONS = False

	DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"
	USER_AGENT_FORMAT = ("Browser: {browser} | Platform: {platform}"
 						" | Language: {language} | Version: {version}")

	BASE_DIR = Path(__file__).resolve().parent
	MIGRATIONS_DIR = BASE_DIR.parent.joinpath("migrations")
	LOGS_DIR = BASE_DIR.joinpath("logs")
	MEDIA_DIR = BASE_DIR.joinpath("media")
	IMAGES_DIR = MEDIA_DIR.joinpath("images")
	TESTS_DIR = BASE_DIR.parent.joinpath("tests")

	IMAGES_MIN_SIZE = (500, 500)
	IMAGES_MAX_SIZE = (1920, 1080)
	IMAGES_ALLOWED_EXTENSIONS = {"jpeg", "jpg", "png"}
	DEFAULT_USER_IMAGE_FILENAME = "user-default.png"
	USER_ALLOWED_HTML_TAGS = {"a", "b", "strong", "code", "i", "em"}
	USER_WARNINGS_MAX_COUNT = 3

	MAIL_TOKENS_MAX_AGE = datetime.timedelta(minutes=10)

	TAGS_PER_PAGE = 5
	POSTS_PER_PAGE = 3
	POST_LIKES_PER_PAGE = 5
	POST_COMMENTS_PER_PAGE = 5
	ACTION_LOGS_PER_PAGE = 5
	NOTIFICATIONS_PER_PAGE = 15

	RESERVED_TAG_NAMES = {"create"}
	RESERVED_POST_SLUGS = {"create", "search"}

	CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']
	CELERY_RESULT_BACKEND = CELERY_BROKER_URL

	MAIL_SERVER = os.environ['MAIL_SERVER']
	MAIL_PORT = os.environ['MAIL_PORT']
	MAIL_USERNAME = os.environ['MAIL_USERNAME']
	MAIL_PASSWORD = os.environ['MAIL_PASSWORD']
	MAIL_DEFAULT_SENDER = (os.environ['MAIL_DEFAULT_SENDER_NAME'], MAIL_USERNAME)
	MAIL_USE_TLS = False
	MAIL_USE_SSL = False
	MAIL_DEBUG = False

	RECAPTCHA_PUBLIC_KEY = os.environ['RECAPTCHA_PUBLIC_KEY']
	RECAPTCHA_PRIVATE_KEY = os.environ['RECAPTCHA_PRIVATE_KEY']

	GITHUB_OAUTH_CLIENT_ID = os.environ['GITHUB_OAUTH_CLIENT_ID']
	GITHUB_OAUTH_CLIENT_SECRET = os.environ['GITHUB_OAUTH_CLIENT_SECRET']


class ProductionConfig(BaseConfig):
	DEBUG = False

	ACTION_LOGS_STORAGE_URL = "redis://action-logs-storage:6379/0"
	SQLALCHEMY_DATABASE_URI = _get_postgresql_database_uri()


class TestingConfig(BaseConfig):
	TESTING = True
	WTF_CSRF_ENABLED = False

	MEDIA_DIR = BaseConfig.BASE_DIR.joinpath("test_media")
	IMAGES_DIR = MEDIA_DIR.joinpath("images")
	OAUTH_CASSETTES_DIR = BaseConfig.TESTS_DIR.joinpath("cassettes")

	DATABASE_PATH = BaseConfig.TESTS_DIR.joinpath("testing.db")
	SQLALCHEMY_DATABASE_URI = "sqlite:///" + str(DATABASE_PATH)

	# NOTE: During the first tests it must be specified to register
	# samples (cassettes) of OAuth requests in `TESTS_DIR/cassettes`. After the
	# first successful tests this parameter can be permanently deleted from `.env`.
	GITHUB_OAUTH_ACCESS_TOKEN = os.environ.get("GITHUB_OAUTH_ACCESS_TOKEN", "fake-token")
