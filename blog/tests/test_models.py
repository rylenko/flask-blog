import pytest
from flask import url_for, session

from app import db


def test_user_on_changed_email(app, test_confirmed_user):
	test_confirmed_user.email = test_confirmed_user.email.upper()
	db.session.commit()
	assert test_confirmed_user.email.islower()
	assert test_confirmed_user.email_is_confirmed

	test_confirmed_user.email = "qwe@QWE.qwe"
	db.session.commit()
	assert test_confirmed_user.email.islower()
	assert not test_confirmed_user.email_is_confirmed


def test_user_on_changed_warnings(app, test_user):
	test_user.warnings += app.config['USER_WARNINGS_MAX_COUNT']
	db.session.commit()
	assert not test_user.is_active


def test_user_on_changed_totp_is_enabled(app, test_user):
	old_secret_key = test_user.secret_key
	test_user.totp_is_enabled = True
	db.session.commit()

	test_user.totp_is_enabled = False
	db.session.commit()

	assert test_user.secret_key != old_secret_key


def test_session_before_delete(app, client):
	with client() as c:
		c.get(url_for("main.index"))  # Initialize session

		with pytest.raises(ValueError):
			db.session.delete(session.get_database_object())
			db.session.commit()


def test_mailtoken_on_changed_type(app, test_user):
	with pytest.raises(ValueError):
		test_user.create_active_mail_token("invalid-type")


def test_notification_on_changed_recipient(app, test_user):
	test_user.is_receiving_notifications = False
	db.session.commit()

	with pytest.raises(ValueError):
		test_user.send_notification("test")


def test_post_before_save(app, test_post):
	test_post.slug = None
	db.session.commit()
	assert test_post.slug[-10:].isdigit()  # type: ignore


def test_post_before_delete(app, test_post):
	image_path = app.config['IMAGES_DIR'].joinpath(test_post.image_filename)
	assert image_path.exists()

	db.session.delete(test_post)
	db.session.commit()
	assert not image_path.exists()


def test_post_comment_on_changed_text(app, test_post_comment):
	test_post_comment.text = "**bold**"
	db.session.commit()
	assert test_post_comment.text == "<strong>bold</strong>"
