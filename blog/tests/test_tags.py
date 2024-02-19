from flask import url_for

from .utils import check_response_ok
from app.models import Tag


def test_regular_routes(client, test_tag):
	endpoints = ("index",)
	detail_endpoints = {'detail': {'name': test_tag.name}}

	with client() as c:
		for e in endpoints:
			assert check_response_ok(c, "tags." + e)
		for e, opts in detail_endpoints.items():
			assert check_response_ok(c, "tags." + e, **opts)


def test_create(client, test_admin_user):
	url = url_for("tags.create")

	with client(user=test_admin_user) as c:
		response = c.post(url, data={
			'name': "Test-Tag-Name",
		})

	assert response.status_code == 302
	assert Tag.query.filter_by(name="Test-Tag-Name").first() is not None


def test_update(client, test_admin_user, test_tag):
	url = url_for("tags.update", name=test_tag.name)

	with client(user=test_admin_user) as c:
		response = c.post(url, data={
			'name': "updated-tag-name",
		})

	assert response.status_code == 302
	assert test_tag.name == "updated-tag-name"


def test_delete(client, test_admin_user, test_tag):
	url = url_for("tags.delete", name=test_tag.name)

	with client(user=test_admin_user) as c:
		response = c.post(url)

	assert response.status_code == 302
	assert Tag.query.get(test_tag.id) is None
