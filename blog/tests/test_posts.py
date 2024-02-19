from flask import url_for

from .utils import check_response_ok
from app.models import Post, PostComment


def test_regular_routes(client, test_post, test_post_comment):
	endpoints = ("index",)
	detail_endpoints = {'detail': {'slug': test_post.slug}}

	with client() as c:
		for e in endpoints:
			assert check_response_ok(c, "posts." + e)
		for e, opts in detail_endpoints.items():
			assert check_response_ok(c, "posts." + e, **opts)


def test_create(client, test_admin_user, test_tag, test_image_io):
	url = url_for("posts.create")

	with client(user=test_admin_user) as c:
		response = c.post(url, data={
			'image': (test_image_io, "test-image.jpg"),
			'title': "test-post-title",
			'preview_text': "test-post-preview-text",
			'text': "test-post-text",
			'tags': [test_tag.id],
		})

	created_post = Post.query.filter_by(title="test-post-title").first()

	assert response.status_code == 302
	assert created_post is not None
	assert created_post.tags[0] is test_tag


def test_update(client, test_admin_user, test_post, test_tag):
	url = url_for("posts.update", slug=test_post.slug)

	with client(user=test_admin_user) as c:
		response = c.post(url, data={
			'title': "updated-test-post",
			'preview_text': "updated-test-post-preview-text",
			'text': "updated-test-post-text",
			'slug': "updated-test-post-slug",
			'tags': [test_tag.id],
		})

	assert response.status_code == 302
	assert test_post.title == "updated-test-post"
	assert test_post.slug == "updated-test-post-slug"
	assert test_post.tags[0] is test_tag


def test_delete(client, test_admin_user, test_post):
	url = url_for("posts.delete", slug=test_post.slug)

	with client(user=test_admin_user) as c:
		response = c.post(url)

	assert response.status_code == 302
	assert Post.query.get(test_post.id) is None


def test_like_and_unlike(client, test_confirmed_user, test_post):
	# Test like -----------------------------------------------
	like_url = url_for("posts.like", slug=test_post.slug)

	with client(user=test_confirmed_user) as c:
		response = c.post(like_url)

	assert response.status_code == 302
	assert test_post.check_like(sender=test_confirmed_user)

	# Test unlike ---------------------------------------------
	unlike_url = url_for("posts.unlike", slug=test_post.slug)

	with client(user=test_confirmed_user) as c:
		response = c.post(unlike_url)

	assert response.status_code == 302
	assert not test_post.check_like(sender=test_confirmed_user)


def test_comment(client, test_confirmed_user, test_post):
	url = url_for("posts.comment", slug=test_post.slug)

	with client(user=test_confirmed_user) as c:
		response = c.post(url, data={
			'text': "test-comment",
		})

	assert response.status_code == 302
	assert PostComment.query.filter_by(
		post=test_post, text="test-comment",
		author=test_confirmed_user).first() is not None


def test_reply_comment(client, test_confirmed_user, test_post_comment):
	url = url_for("posts.reply_comment", id=test_post_comment.id)

	with client(user=test_confirmed_user) as c:
		response = c.post(url, data={
			'text': "test-reply-comment",
		})

	created_reply_comment = PostComment.query.filter_by(
		author=test_confirmed_user,
		parent=test_post_comment,
		text="test-reply-comment",
	).first()

	assert response.status_code == 302
	assert created_reply_comment is not None
	assert created_reply_comment.parent is test_post_comment


def test_update_comment(client, test_post_comment):
	url = url_for("posts.update_comment", id=test_post_comment.id)

	with client(user=test_post_comment.author) as c:
		response = c.post(url, data={
			'text': "test-update-post-comment",
		})

	assert response.status_code == 302
	assert test_post_comment.text == "test-update-post-comment"


def test_delete_comment(client, test_post_comment):
	url = url_for("posts.delete_comment", id=test_post_comment.id)

	with client(user=test_post_comment.author) as c:
		response = c.post(url)

	assert response.status_code == 302
	assert PostComment.query.get(test_post_comment.id) is None
