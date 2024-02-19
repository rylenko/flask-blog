import shutil
from io import BytesIO
from typing import Iterator

import pytest
import celery
from PIL import Image
from betamax import Betamax
from flask import Flask, Response
from flask_dance.consumer.storage import MemoryStorage

from .utils import Client, create_test_user, register_auxiliary_routes
from app import db, create_app
from app.config import TestingConfig
from app.utils import save_image_in_memory
from app.models import Tag, User, Post, PostComment, Notification
from app.accounts.oauth import accounts_github_bp


@pytest.fixture
def app() -> Iterator[Flask]:
	for dir_ in (
		TestingConfig.IMAGES_DIR,
		TestingConfig.OAUTH_CASSETTES_DIR,
	):
		if not dir_.exists():
			dir_.mkdir(parents=True)

	rv = create_app(TestingConfig)
	rv.test_client_class = Client
	register_auxiliary_routes(rv)

	with rv.app_context():
		db.create_all()
		yield rv
		db.drop_all()

	TestingConfig.DATABASE_PATH.unlink()
	shutil.rmtree(TestingConfig.MEDIA_DIR)
	celery.current_app.control.purge()


@pytest.fixture
def client(app) -> Client:
	return app.test_client


@pytest.fixture
def test_user() -> User:
	return create_test_user()


@pytest.fixture
def test_totp_user() -> User:
	return create_test_user(totp_is_enabled=True)


@pytest.fixture
def test_confirmed_user() -> User:
	return create_test_user(email_is_confirmed=True)


@pytest.fixture
def test_admin_user() -> User:
	return create_test_user(is_staff=True, email_is_confirmed=True)


@pytest.fixture
def test_notification(test_user) -> Notification:
	rv = test_user.send_notification("test-notification-text")
	db.session.commit()
	return rv


@pytest.fixture
def test_post(test_admin_user, test_image) -> Post:
	rv = Post(image_filename=test_image, author=test_admin_user,
  			title="test-post-title", text="test-post-text",
  			preview_text="test-post-preview-text")
	db.session.add(rv)
	db.session.commit()

	return rv


@pytest.fixture
def test_post_comment(test_confirmed_user, test_post) -> PostComment:
	rv = test_post.add_comment("test-post-comment-text", author=test_confirmed_user)
	db.session.add(rv)
	db.session.commit()

	return rv


@pytest.fixture
def test_tag() -> Tag:
	rv = Tag(name="test-tag-name")
	db.session.add(rv)
	db.session.commit()

	return rv


@pytest.fixture
def test_image(app) -> str:
	filename = "test-image.jpg"
	path = app.config['IMAGES_DIR'].joinpath(filename)

	image = Image.new("RGB", (512, 512), color="red")
	image.save(path, optimize=True, quality=95)

	return filename


@pytest.fixture
def test_image_io() -> BytesIO:
	image = Image.new("RGB", (512, 512), color="red")
	return save_image_in_memory(image, "JPEG")


@pytest.fixture
def betamax_github_app(app, monkeypatch, request) -> Flask:
	"""Use this fixture, not `app` if you work with GitHub OAuth. This device
	records the whole process of OAuth data exchange, after that writing all the
	information into `OAUTH_CASSETES_DIR` for further use as samples (cassettes)."""

	# Without it, `Flask` will give out an error at what we
	# register next `after_request` in the `before_request` body.
	app.debug = False

	@app.before_request
	def wrap() -> None:
		recorder = Betamax(accounts_github_bp.session)
		recorder.use_cassette(request.node.name)
		recorder.start()

		@app.after_request
		def unwrap(response: Response) -> Response:
			recorder.stop()
			return response

		request.addfinalizer(lambda: app.after_request_funcs[None].remove(unwrap))

	request.addfinalizer(lambda: app.before_request_funcs[None].remove(wrap))

	storage = MemoryStorage({'access_token': app.config['GITHUB_OAUTH_ACCESS_TOKEN']})
	monkeypatch.setattr(accounts_github_bp, "storage", storage)

	return app


@pytest.fixture
def betamax_github_client(betamax_github_app) -> Client:
	"""Use this client when dealing with GitHub OAuth requests. This client includes
	the required `before_request` and `after_request` from `betamax_github_app`."""
	return betamax_github_app.test_client
