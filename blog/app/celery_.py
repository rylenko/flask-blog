from typing import Any

from celery import Celery

from . import create_app


def make_celery() -> Celery:
	"""The main task of this function is to force celery
	to run tasks only under the context of our application."""

	app = create_app()
	celery = Celery(app.import_name,
					broker=app.config['CELERY_BROKER_URL'],
					backend=app.config['CELERY_RESULT_BACKEND'])
	celery.conf.update(accept_content=['json'], task_serializer="json")

	class ContextTask(celery.Task):  # type: ignore
		abstract = True

		def __call__(self, *args: Any, **kwargs: Any) -> Any:
			with app.app_context():
				return super().__call__(*args, **kwargs)

	celery.Task = ContextTask

	return celery
