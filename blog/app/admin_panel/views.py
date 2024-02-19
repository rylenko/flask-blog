from typing import Any
from datetime import datetime
from collections.abc import Mapping

from flask import abort, Markup, url_for, session, request, redirect, current_app
from flask_admin.base import expose
from flask_admin.contrib.rediscli import RedisCli

from .base import ModelView, AdminRequiredMixin
from .forms import OAuthProviderSelectField, MailTokenTypeSelectField
from .utils import (
	make_related_post_link,
	make_related_user_link,
	make_related_post_comment_link,
)
from .. import csrf
from ..models import (
	Tag,
	User,
	Post,
	OAuth,
	Session,
	PostLike,
	MailToken,
	PostComment,
	Notification,
)


class UserView(ModelView):
	model = User
	can_create = False
	can_delete = False
	column_list = ("id", "email", "username", "is_active", "is_staff", "last_online")
	column_searchable_list = ("id", "email", "username", "information", "location")
	form_excluded_columns = ("notifications", "post_likes", "post_comments")


class SessionView(ModelView):
	model = Session
	can_create = False
	column_list = ("id", "key", "user", "agent", "last_online")
	column_searchable_list = ("id", "key", "user_id", "agent")
	column_formatters = {'user': make_related_user_link}
	form_excluded_columns = ("data",)

	def delete_model(self, instance: Session):
		if instance.key == session.key:  # type: ignore
			# We can't terminate a current session
			abort(403)
		return super().delete_model(instance)


class ActionLogsView(AdminRequiredMixin, RedisCli):
	@expose("/run/", methods=("POST",))
	@csrf.exempt
	def execute_view(self):
		"""The same `execute_view`, but with `csrf.exempt`,
		as its control is not provided in `RedisCli`"""
		return super().execute_view()

	@staticmethod
	def _strftime(ts: str, /) -> str:
		dt = datetime.utcfromtimestamp(float(ts))
		return dt.strftime(current_app.config['DATETIME_FORMAT'])

	def _result(self, result: Any) -> str:
		"""Makes the timestamp keys of the logs readable. For
		example, turn `1602752022.140108` into `15.10.2020 15:53:42`
		or something else, depending on `DATETIME_FORMAT`."""

		if not isinstance(result, Mapping):
			return super()._result(result)

		result = {self._strftime(ts): msg
  				for ts, msg in result.items()}
		return super()._result(result)


class OAuthView(ModelView):
	model = OAuth
	column_list = ("id", "user", "provider", "created_at")
	column_searchable_list = ("id", "user_id", "social_id", "provider")
	column_formatters = {'user': make_related_user_link}
	form_overrides = {'provider': OAuthProviderSelectField}


class MailTokenView(ModelView):
	model = MailToken
	column_list = ("id", "owner", "type", "key", "expires_at")
	column_searchable_list = ("id", "owner_id", "key", "type")
	column_formatters = {'owner': make_related_user_link}
	form_overrides = {'type': MailTokenTypeSelectField}


class NotificationView(ModelView):
	model = Notification
	column_list = ("id", "recipient", "is_checked", "text")
	column_searchable_list = ("id", "text")
	column_formatters = {'recipient': make_related_user_link,
 						'text': lambda v, c, i, f: Markup(getattr(i, f))}


class PostView(ModelView):
	model = Post
	column_list = ("id", "author", "title", "slug", "created_at")
	column_searchable_list = ("id", "title", "preview_text", "text", "slug")
	column_formatters = {'author': make_related_user_link}
	form_excluded_columns = ("likes", "comments")

	@expose("/new/", methods=("GET", "POST"))
	def create_view(self):
		return redirect(url_for("posts.create"))

	@expose("/edit/", methods=("GET", "POST"))
	def edit_view(self):
		post = Post.query.get_or_404(request.args.get("id", type=int))
		return redirect(url_for("posts.update", slug=post.slug))

	@expose("/delete/", methods=("GET", "POST"))
	def delete_view(self):
		post = Post.query.get_or_404(self.delete_form().id.data)
		return redirect(url_for("posts.delete", slug=post.slug))


class PostLikeView(ModelView):
	model = PostLike
	column_list = ("id", "sender", "post", "created_at")
	column_searchable_list = ("id", "sender_id", "post_id")
	column_formatters = {'sender': make_related_user_link,
 						'post': make_related_post_link}


class PostCommentView(ModelView):
	model = PostComment
	form_excluded_columns = ("replies",)
	column_list = ("id", "author", "post", "text", "parent", "created_at")
	column_searchable_list = ("id", "author_id", "post_id", "text")
	column_formatters = {'author': make_related_user_link,
 						'post': make_related_post_link,
 						'parent': make_related_post_comment_link}

	@expose("/edit/", methods=("GET", "POST"))
	def edit_view(self):
		id_ = request.args.get("id", type=int)
		return redirect(url_for("posts.update_comment", id=id_))


class TagView(ModelView):
	model = Tag
	column_list = ("id", "name", "created_at")
	column_searchable_list = ("id", "name")
	form_excluded_columns = ("posts",)

	@expose("/new/", methods=("GET", "POST"))
	def create_view(self):
		return redirect(url_for("tags.create"))

	@expose("/edit/", methods=("GET", "POST"))
	def edit_view(self):
		tag = Tag.query.get_or_404(request.args.get("id", type=int))
		return redirect(url_for("tags.update", name=tag.name))

	@expose("/delete/", methods=("GET", "POST"))
	def delete_view(self):
		tag = Tag.query.get_or_404(self.delete_form().id.data)
		return redirect(url_for("tags.delete", name=tag.name))
