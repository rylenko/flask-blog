from flask import Blueprint


tags_bp = Blueprint("tags", __name__)


from . import views  # noqa
