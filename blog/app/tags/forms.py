from typing import Any, Optional

from flask import current_app
from flask_babel import _
from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import validators, StringField

from .. import db
from .. import fields as common
from ..models import Tag
from ..utils import _make_avoiding_condition


class TagForm(FlaskForm):
	name_min_length = 3
	name_max_length = 50

	name = StringField(
		label=_l("Name"),
		validators=(
			validators.DataRequired(message=_l("Name field is required.")),
			validators.Length(min=name_min_length, max=name_max_length, message=_l(
				"Name length must not be less than "
				"%(min)d and more than %(max)d characters."
			)),
		),
		render_kw={
			'class': "form-control",
			'minlength': name_min_length, 'maxlength': name_max_length,
			'placeholder': _l("Enter the name of your new tag..."),
		},
	)
	submit = common.SubmitField(render_kw={
		'class': "btn btn-success",
		'value': _l("Create"),
	})

	def __init__(self, *args: Any,
 				obj_on_update: Optional[Tag] = None, **kwargs: Any) -> None:
		self.obj_on_update = obj_on_update
		super().__init__(*args, **kwargs)

	def populate(self) -> Tag:
		rv = self.obj_on_update or Tag()
		self.populate_obj(rv)

		if self.obj_on_update is None:
			db.session.add(rv)
		return rv

	def validate_name(self, field: StringField) -> None:
		unique_conditions = [Tag.name == field.data]

		if self.obj_on_update is not None:
			unique_conditions.append(_make_avoiding_condition(self.obj_on_update))

		if field.data in current_app.config['RESERVED_TAG_NAMES']:
			raise validators.ValidationError(_("You cannot create a tag with this name."))
		elif Tag.query.filter(*unique_conditions).first() is not None:
			raise validators.ValidationError(_("Tag with this name already exists."))
