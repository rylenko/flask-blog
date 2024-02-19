from typing import Optional

from flask import Markup, url_for
from jinja2.runtime import Context

from .base import ModelView
from ..models import BaseModel


def _make_html_link(title: str, /, href: str) -> Markup:
	return Markup(f"<a href=\"{href}\">{title}</a>")


def make_related_user_link(
	view: ModelView, ctx: Context,
	instance: BaseModel, user_field_name: str,
) -> Optional[Markup]:
	user = getattr(instance, user_field_name)
	if user is None:
		return None
	href = url_for("users.detail", username=user.username)
	return _make_html_link(user.username, href=href)


def make_related_post_link(
	view: ModelView, ctx: Context,
	instance: BaseModel, post_field_name: str,
) -> Optional[Markup]:
	post = getattr(instance, post_field_name)
	if post is None:
		return None
	href = url_for("posts.detail", slug=post.slug)
	return _make_html_link(post.title, href=href)


def make_related_post_comment_link(
	view: ModelView, ctx: Context,
	instance: BaseModel, comment_field_name: str,
) -> Optional[Markup]:
	comment = getattr(instance, comment_field_name)
	if comment is None:
		return None
	href = url_for("posts.detail", slug=comment.post.slug)
	return _make_html_link(comment.text[:20] + "...", href=href)
