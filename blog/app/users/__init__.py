from flask import Blueprint


users_bp = Blueprint("users", __name__)


from . import views  # noqa
