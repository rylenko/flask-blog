from app.utils import paginate, get_next_url, save_image


def test_save_image(app, test_user, test_image_io):
	filename = save_image(test_image_io)
	assert app.config['IMAGES_DIR'].joinpath(filename).exists()


def test_get_next_url_fail(app):
	url = "http://bad-site.com/"
	with app.test_request_context("?next=" + url):
		assert get_next_url() is None


def test_get_next_url_success(app):
	url = "http://localhost/accounts/profile/"
	with app.test_request_context("?next=" + url):
		assert get_next_url() == url


def test_paginate(app):
	elements = (1, 2, 3, 4, 5, 6, 7, 8)

	with app.test_request_context("?page=3"):
		assert paginate(elements, 2).items == (5, 6)
