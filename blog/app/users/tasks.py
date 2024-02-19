from .. import db
from ..models import User
from ..celery_ import make_celery


celery = make_celery()


@celery.task
def send_everyone_notification_task(text: str) -> None:
	for user in User.query.filter_by(is_receiving_notifications=True).all():
		user.send_notification(text)
	db.session.commit()
