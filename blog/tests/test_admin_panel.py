from flask import url_for


def test_admin_required_mixin(client, test_user, test_admin_user):
	url = url_for("admin.index")

	with client(user=test_user) as c:
		response = c.get(url)
		assert response.status_code == 404

	with client(user=test_admin_user) as c:
		with c.session_transaction() as session:
			session['password_was_once_confirmed'] = False

		response = c.get(url)
		assert response.status_code == 200
		assert b"Enter your password" in response.data

		response = c.post(url, data={'password': "test-user-password"})
		assert response.status_code == 302
