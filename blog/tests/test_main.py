from io import BytesIO

from PIL import Image

from .utils import check_response_ok
from app.utils import get_image_url


def test_regular_routes(client):
	endpoints = ("index",)

	with client() as c:
		for e in endpoints:
			assert check_response_ok(c, "main." + e)


def test_image(app, client, test_image):
	path = app.config['IMAGES_DIR'].joinpath(test_image)
	url = get_image_url(filename=test_image)

	with client() as c:
		response = c.get(url)

	assert response.status_code == 200

	response_image = BytesIO(response.data)
	with Image.open(response_image) as image:
		with Image.open(path) as original_image:
			assert image == original_image


def test_image_custom_size(app, client, test_image):
	url = get_image_url(filename=test_image, size=335)

	with client() as c:
		response = c.get(url)

	assert response.status_code == 200

	response_image = BytesIO(response.data)
	with Image.open(response_image) as image:
		assert image.size == (335, 335)
