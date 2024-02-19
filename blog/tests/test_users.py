from flask import url_for

from .utils import check_response_ok


def test_regular_routes(client, test_user, test_confirmed_user):
	confirmed_user_endpoints = {'detail': {'username': test_user.username}}

	with client(user=test_confirmed_user) as c:
		for e, opts in confirmed_user_endpoints.items():
			assert check_response_ok(c, "users." + e, **opts)


def test_warn(client, test_user, test_admin_user):
	url = url_for("users.warn", username=test_user.username)

	with client(user=test_admin_user) as c:
		response = c.post(url)

	assert response.status_code == 302
	assert test_user.warnings == 1
	assert test_user.notifications.count() == 1
