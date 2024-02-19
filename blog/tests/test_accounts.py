import pyotp
from flask import url_for, session, get_flashed_messages

from .utils import check_response_ok, check_is_authenticated
from app import db
from app.models import User, OAuth, MailToken


def _generate_confirm_email_act_url(test_user: User) -> str:
	new_token = test_user.create_active_mail_token(MailToken.EMAIL_CONFIRM_TYPE)
	db.session.commit()
	return url_for("accounts.confirm_email_act", mail_token_key=new_token.key)


def _generate_reset_password_act_url(test_user: User) -> str:
	new_token = test_user.create_active_mail_token(MailToken.PASSWORD_RESET_TYPE)
	db.session.commit()
	return url_for("accounts.reset_password_act", mail_token_key=new_token.key)


def test_regular_routes(client, test_user, test_confirmed_user):
	endpoints = ("reset_password",)
	user_endpoints = ("confirm_email", "totp_qrcode", "notifications",
  					"notifications_count", "oauths", "post_comments",
  					"post_likes", "profile", "sessions")
	confirmed_user_endpoints = ("confirm_email_done",)

	with client() as c:
		for e in endpoints:
			assert check_response_ok(c, "accounts." + e)

	with client(user=test_user) as c:
		for e in user_endpoints:
			assert check_response_ok(c, "accounts." + e)

	with client(user=test_confirmed_user) as c:
		for e in confirmed_user_endpoints:
			assert check_response_ok(c, "accounts." + e)


def test_check_notification(client, test_user, test_notification):
	url = url_for("accounts.check_notification", id=test_notification.id)

	with client(user=test_user) as c:
		response = c.post(url)

	assert response.status_code == 302
	assert test_notification.is_checked


def test_delete_notifications(client, test_user):
	for i in range(10):
		test_user.send_notification(str(i))
	db.session.commit()
	assert test_user.notifications.count() == 10

	url = url_for("accounts.delete_notifications")

	with client(user=test_user) as c:
		c.post(url)

	assert test_user.notifications.count() == 0


def test_login_success(client, test_user):
	url = url_for("accounts.login")

	with client() as c:
		response = c.post(url, data={
			'email': test_user.email,
			'password': "test-user-password",
		})

		assert response.status_code == 302
		assert check_is_authenticated(c)


def test_login_fail(client, test_user):
	url = url_for("accounts.login")

	with client() as c:
		response = c.post(url, data={
			'email': test_user.email,
			'password': "not-test-user-password",
		})

		assert response.status_code == 200
		assert not check_is_authenticated(c)


def test_login_two_factor_success(client, test_totp_user):
	login_url = url_for("accounts.login")
	login_totp_url = url_for("accounts.login_two_factor")

	with client() as c:
		login_response = c.post(login_url, data={
			'email': test_totp_user.email,
			'password': "test-user-password",
		})
		assert login_response.status_code == 302
		assert not check_is_authenticated(c)
		assert session['login_two_factor'] == {
			'user_id': test_totp_user.id,
			'next_url': None,
		}

		totp_response = c.post(login_totp_url, data={
			'totp': pyotp.TOTP(test_totp_user.secret_key).now(),
		})
		assert totp_response.status_code == 302
		assert check_is_authenticated(c)
		assert "login_two_factor" not in session


def test_login_two_factor_fail(client, test_totp_user):
	login_url = url_for("accounts.login")
	login_totp_url = url_for("accounts.login_two_factor")

	with client() as c:
		login_response = c.post(login_url, data={
			'email': test_totp_user.email,
			'password': "test-user-password",
		})
		assert login_response.status_code == 302
		assert not check_is_authenticated(c)
		assert session['login_two_factor'] == {
			'user_id': test_totp_user.id,
			'next_url': None,
		}

		totp_response = c.post(login_totp_url, data={
			'totp': "123456",
		})
		assert totp_response.status_code == 200
		assert not check_is_authenticated(c)
		assert session['login_two_factor'] == {
			'user_id': test_totp_user.id,
			'next_url': None,
		}


def test_login_two_factor_backup_code(client, test_totp_user):
	codes = test_totp_user.genset_backup_codes()
	db.session.commit()

	login_url = url_for("accounts.login")
	login_backup_code_url = url_for("accounts.login_two_factor_backup_code")

	with client() as c:
		login_response = c.post(login_url, data={
			'email': test_totp_user.email,
			'password': "test-user-password",
		})
		assert login_response.status_code == 302
		assert not check_is_authenticated(c)
		assert session['login_two_factor'] == {
			'user_id': test_totp_user.id,
			'next_url': None,
		}

		backup_code_response = c.post(login_backup_code_url, data={
			'backup_code': codes[0],
		})
		assert backup_code_response.status_code == 302
		assert check_is_authenticated(c)
		assert len(test_totp_user.backup_code_hashes) == len(codes) - 1
		assert not test_totp_user.check_backup_code(codes[0])
		assert "login_two_factor" not in session


def test_register_success(client):
	url = url_for("accounts.register")

	with client() as c:
		response = c.post(url, data={
			'email': "test-register@us.er",
			'username': "test-register-user",
			'password': "test-register-user-password",
			'password_confirm': "test-register-user-password",
		})

		assert response.status_code == 302
		assert User.query.filter_by(email="test-register@us.er").first() is not None
		assert check_is_authenticated(c)


def test_register_fail(client, test_user):
	url = url_for("accounts.register")

	with client() as c:
		response = c.post(url, data={
			'email': test_user.email,
			'username': test_user.username,
			'password': "user-password",
			'password_confirm': "user-password",
		})

		assert response.status_code == 200
		assert User.query.order_by(User.id.desc()).first() is test_user
		assert not check_is_authenticated(c)


def test_terminate_session(client, test_user):
	with client(user=test_user) as c:
		assert test_user.sessions.count() == 1
	first_session = test_user.sessions.all()[0]

	with client(user=test_user) as c:
		assert test_user.sessions.count() == 2
		url = url_for("accounts.terminate_session", id=first_session.id)
		response = c.post(url)

	assert response.status_code == 302
	assert test_user.sessions.count() == 1
	assert first_session not in test_user.sessions.all()


def test_unbind_oauth(client, test_user):
	test_oauth = OAuth(provider="github", token={'fake': "token"}, social_id=1)
	db.session.add(test_oauth)
	test_user.oauths.append(test_oauth)

	db.session.commit()

	url = url_for("accounts.unbind_oauth", provider="github")

	with client(user=test_user) as c:
		response = c.post(url)

	assert response.status_code == 302
	assert test_oauth not in test_user.oauths


def test_oauth_github_register_or_login(betamax_github_client):
	with betamax_github_client() as c:
		response = c.get(url_for("accounts.oauths_github"))
		assert check_is_authenticated(c)
		assert "successfully registered" in get_flashed_messages()[0]

	created_oauth = OAuth.query.first()

	assert response.status_code == 302
	assert created_oauth is not None
	assert created_oauth.provider == "github"
	assert created_oauth.user is not None
	# Confirms that it is registered through OAuth
	assert created_oauth.user.password_hash is None

	with betamax_github_client() as c:
		c.get(url_for("accounts.oauths_github"))
		assert check_is_authenticated(c)
		assert "successfully logged in" in get_flashed_messages()[0]


def test_oauth_github_bind(betamax_github_client, test_user):
	with betamax_github_client(user=test_user) as c:
		response = c.get(url_for("accounts.oauths_github"))
		assert "successfully bind" in get_flashed_messages()[0]

	assert response.status_code == 302
	assert test_user.oauths.count() == 1
	assert test_user.oauths[0].provider == "github"

	with betamax_github_client(user=test_user) as c:
		c.get(url_for("accounts.oauths_github"))
		assert "already applies" in get_flashed_messages()[0]


def test_set_password_successful(client, test_user):
	test_user.password_hash = None
	db.session.commit()

	url = url_for("accounts.set_password")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'new_password': "new-test-user-password",
			'new_password_confirm': "new-test-user-password",
		})

	assert response.status_code == 302
	assert test_user.check_password("new-test-user-password")


def test_set_password_fail(client, test_user):
	test_user.password_hash = None
	db.session.commit()

	url = url_for("accounts.set_password")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'new_password': "qwe",
			'new_password_confirm': "qwe",
		})

	assert response.status_code == 200
	assert test_user.password_hash is None


def test_change_password_successful(client, test_user):
	url = url_for("accounts.change_password")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'old_password': "test-user-password",
			'new_password': "new-test-user-password",
			'new_password_confirm': "new-test-user-password",
		})

	assert response.status_code == 302
	assert test_user.check_password("new-test-user-password")


def test_change_password_fail(client, test_user):
	url = url_for("accounts.change_password")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'old_password': "test-user-password",
			'new_password': "qwe",
			'new_password_confirm': "qwe",
		})

	assert response.status_code == 200
	assert not test_user.check_password("qwe")


def test_update_success(app, client, test_confirmed_user, test_image, test_image_io):
	url = url_for("accounts.update")

	test_confirmed_user.image_filename = test_image
	db.session.commit()

	with client(user=test_confirmed_user) as c:
		response = c.post(url, data={
			'image': (test_image_io, "my-image.jpg"),
			'email': "new-test@user.email",
			'username': "new-test-user-username",
			'information': "",
			'location': "",
		})

	assert response.status_code == 302
	assert test_confirmed_user.email == "new-test@user.email"
	assert not test_confirmed_user.email_is_confirmed
	assert not app.config['IMAGES_DIR'].joinpath(test_image).exists()


def test_update_fail(client, test_user):
	url = url_for("accounts.update")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'email': "qw@q.q",
			'username': "zx",
			'information': "",
			'location': "",
		})

	assert response.status_code == 200
	assert test_user.email != "qw@q.q"


def test_deactivate_success(client, test_user):
	url = url_for("accounts.deactivate")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'password': "test-user-password",
		})

		assert response.status_code == 302
		assert not check_is_authenticated(c)
		assert not test_user.is_active


def test_deactivate_fail(client, test_user):
	url = url_for("accounts.deactivate")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'password': "wrong-password",
		})

		assert response.status_code == 200
		assert check_is_authenticated(c)
		assert test_user.is_active


def test_enable_totp_success(client, test_user):
	url = url_for("accounts.enable_totp")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'totp': pyotp.TOTP(test_user.secret_key).now(),
		})

	assert response.status_code == 302
	assert test_user.totp_is_enabled


def test_enable_totp_fail(client, test_user):
	url = url_for("accounts.enable_totp")

	with client(user=test_user) as c:
		response = c.post(url, data={
			'totp': "123456",
		})

	assert response.status_code == 200
	assert not test_user.totp_is_enabled


def test_disable_totp_success(client, test_totp_user):
	url = url_for("accounts.disable_totp")

	with client(user=test_totp_user) as c:
		response = c.post(url, data={
			'password': "test-user-password",
		})

	assert response.status_code == 302
	assert not test_totp_user.totp_is_enabled


def test_disable_totp_fail(client, test_totp_user):
	url = url_for("accounts.disable_totp")

	with client(user=test_totp_user) as c:
		response = c.post(url, data={
			'password': "invalid-password",
		})

	assert response.status_code == 200
	assert test_totp_user.totp_is_enabled


def test_backup_codes(client, test_totp_user):
	url = url_for("accounts.backup_codes")

	with client(user=test_totp_user) as c:
		response = c.post(url)

	assert response.status_code == 200
	assert test_totp_user.backup_code_hashes


def test_confirm_email_act_success(app, client, test_user):
	url = _generate_confirm_email_act_url(test_user)

	with client(user=test_user) as c:
		response = c.get(url)

	assert response.status_code == 302
	assert test_user.email_is_confirmed
	assert not test_user.has_active_mail_token


def test_confirm_email_act_fail(client, test_user):
	url = url_for("accounts.confirm_email_act", mail_token_key="INVALID-TOKEN")

	with client(user=test_user) as c:
		response = c.get(url)

	assert response.status_code == 404
	assert not test_user.email_is_confirmed


def test_confirm_email_act_token_already_used(app, client, test_user):
	url = _generate_confirm_email_act_url(test_user)

	with client(user=test_user) as c:
		# First request with the same token
		response = c.get(url)
		assert response.status_code == 302

		# Zeroing so that the 'email_unconfirmed_required'
		# decorator does not interfere
		test_user.email_is_confirmed = False
		db.session.commit()

		# Second request with the same token
		response = c.get(url)
		assert response.status_code == 404


def test_confirm_email_act_use_strange_token(app, client, test_user):
	url = _generate_confirm_email_act_url(test_user)

	second_test_user = User(email="second@test.user", username="second-test-user")
	db.session.add(second_test_user)
	db.session.commit()

	with client(user=second_test_user) as c:
		response = c.get(url)

	assert response.status_code == 404


def test_reset_password_act_success(client, test_user):
	url = _generate_reset_password_act_url(test_user)

	with client() as c:
		response = c.post(url, data={
			'new_password': "test-reset-password-successful",
			'new_password_confirm': "test-reset-password-successful",
		})

	assert response.status_code == 200
	assert test_user.check_password("test-reset-password-successful")
	assert not test_user.has_active_mail_token


def test_reset_password_act_fail(client, test_user):
	url = url_for("accounts.reset_password_act", mail_token_key="INVALID-TOKEN")

	with client() as c:
		response = c.post(url, data={
			'new_password': "test-reset-password-fail",
			'new_password_confirm': "test-reset-password-fail",
		})

	assert response.status_code == 404
	assert not test_user.check_password("test-reset-password-fail")


def test_reset_password_act_token_already_used(client, test_user):
	url = _generate_reset_password_act_url(test_user)

	with client() as c:
		# First request with the same token
		response = c.post(url, data={
			'new_password': "test-reset-password-fail",
			'new_password_confirm': "test-reset-password-fail",
		})
		assert response.status_code == 200

		# Second request with the same token
		response = c.get(url)
		assert response.status_code == 404
