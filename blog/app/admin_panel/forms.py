from typing import Any

from flask import current_app
from flask_dance.consumer.base import BaseOAuthConsumerBlueprint
from wtforms import SelectField

from ..models import MailToken


class OAuthProviderSelectField(SelectField):
	def __init__(self, *args: Any, **kwargs: Any) -> None:
		kwargs['choices'] = []

		for b_name, b in current_app.blueprints.items():
			if isinstance(b, BaseOAuthConsumerBlueprint):
				kwargs['choices'].append((b_name, b_name))

		super().__init__(*args, **kwargs)


class MailTokenTypeSelectField(SelectField):
	def __init__(self, *args: Any, **kwargs: Any) -> None:
		kwargs['choices'] = [(t, t) for t in MailToken.get_types()]
		super().__init__(*args, **kwargs)
