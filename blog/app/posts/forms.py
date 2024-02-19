from typing import Any, Optional

from flask import current_app
from flask_wtf import FlaskForm
from flask_login import current_user
from flask_babel import _
from flask_babel import lazy_gettext as _l
from wtforms import validators, StringField, TextAreaField, SelectMultipleField

from .. import db
from .. import fields as common
from ..models import Tag, Post
from ..utils import _make_avoiding_condition


class PostForm(FlaskForm):
	title_min_length = 5
	title_max_length = 140
	slug_max_length = 140

	image = common.ImageField()
	title = StringField(
		label=_l("Title"),
		validators=(
			validators.DataRequired(message=_l("Title field is required.")),
			validators.Length(min=title_min_length, max=title_max_length, message=_l(
				"Title length must not be less than "
				"%(min)d and more than %(max)d characters."
			)),
		),
		render_kw={
			'class': "form-control", 'placeholder': _l("Enter title of your post..."),
			'minlength': title_min_length, 'maxlength': title_max_length,
		},
	)
	preview_text = TextAreaField(
		label=_l("Preview text"),
		validators=(validators.DataRequired(message=_l(
			"Preview text field is required."
		)),),
		render_kw={
			'class': "form-control",
			'placeholder': _l("Enter preview text of your post..."),
		},
	)
	text = TextAreaField(
		label=_l("Text"),
		validators=(validators.DataRequired(message=_l(
			"Text field is required."
		)),),
		render_kw={
			'class': "form-control",
			'placeholder': _l("Enter text of your post..."),
		},
	)
	slug = StringField(
		label=_l("Slug"),
		validators=(validators.Length(max=slug_max_length, message=_l(
			"Slug length must not be more than %(max)d characters."
		)),),
		render_kw={
			'class': "form-control", 'maxlength': slug_max_length,
			'placeholder': _l("Enter slug of your post..."),
		},
	)
	tags = SelectMultipleField(label=_l("Tags"), coerce=int,
   							render_kw={'class': "form-control"})
	submit = common.SubmitField()

	def __init__(self, *args: Any,
 				obj_on_update: Optional[Post] = None, **kwargs: Any) -> None:
		obj_on_which_data_based = kwargs.get("obj")
		self.obj_on_update = obj_on_update

		super().__init__(*args, **kwargs)

		_tags = Tag.query.order_by(Tag.name).all()
		self.tags.choices = [(t.id, t.name) for t in _tags]

		if obj_on_which_data_based is not None:
			# Autoselect in HTML the tags that have already been added
			self.tags.data = [t.id for t in obj_on_which_data_based.tags]

	def _convert_tags_data_identifiers_to_objects(self) -> None:
		self.tags.data = [Tag.query.get(tag_id) for tag_id in self.tags.data]

	def populate(self) -> Post:
		self._convert_tags_data_identifiers_to_objects()
		rv = self.obj_on_update or Post(author=current_user)
		self.populate_obj(rv)

		if self.image.data is not None:
			rv.set_image(self.image.data)

		if self.obj_on_update is None:
			db.session.add(rv)
		return rv

	def validate_slug(self, field: StringField) -> None:
		unique_conditions = [Post.slug == field.data]

		if self.obj_on_update is not None:
			unique_conditions.append(_make_avoiding_condition(self.obj_on_update))

		if field.data in current_app.config['RESERVED_POST_SLUGS']:
			raise validators.ValidationError(_("You cannot create a post with this slug."))
		elif Post.query.filter(*unique_conditions).first() is not None:
			raise validators.ValidationError(_("Post with this slug already exists."))


class PostCommentForm(FlaskForm):
	"""In this model form, unlike others, the `.populate` is
	not implemented due to the excessive clutter. Instead please
	use the `Post.add_comment` or `PostComment.add_reply`,
	etc. manually."""

	max_length = 400

	text = TextAreaField(
		label=_l("New comment (Markdown is supported)"),
		validators=(
			validators.DataRequired(message=_l("Text field is required.")),
			validators.Length(max=max_length, message=_l(
				"Text length must not be more than %(max)d characters."
			)),
		),
		render_kw={
			'class': "form-control",
			'style': "resize: none;", 'maxlength': max_length,
			'placeholder': _l("Enter text of your new comment..."),
		},
	)
	submit = common.SubmitField(render_kw={
		'class': "btn btn-success",
		'value': _l("Submit"),
	})
