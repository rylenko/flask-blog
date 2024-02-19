from flask import flash, url_for, redirect, render_template
from flask_login import login_required
from flask_babel import _

from . import users_bp
from .. import db
from ..decorators import staff_required, email_confirmed_required
from ..models import User, Notification


@users_bp.route("/<username>/")
@login_required
@email_confirmed_required
def detail(username: str):
	user = User.query.filter_by(username=username).first_or_404()
	if not user.is_active:
		return render_template("users/detail-not-active.html")
	return render_template("users/detail.html", user=user)


@users_bp.route("/<username>/warn/", methods=("POST",))
@login_required
@staff_required
def warn(username: str):
	user = User.query.filter_by(username=username, is_active=True,
								is_staff=False).first_or_404()
	user.warnings += 1

	notification = Notification(recipient=user, text=_("A warning has been received."))
	db.session.add(notification)

	db.session.commit()
	flash(_("Your warning has been sent successfully."), "success")
	return redirect(url_for("users.detail", username=user.username))
