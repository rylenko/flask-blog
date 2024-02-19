from app import create_app
from app.celery_ import make_celery


application = create_app()
celery = make_celery()
