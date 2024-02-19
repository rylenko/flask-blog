from flask import flash, request, redirect, render_template
from flask_wtf.csrf import CSRFError
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from . import errors_bp
from .. import db


@errors_bp.app_errorhandler(CSRFError)
def csrf_missing(error: CSRFError):
	return render_template("errors/csrf-missing.html"), 400


@errors_bp.app_errorhandler(IntegrityError)
def integrity(error: IntegrityError):
	flash("IntegrityError: " + str(error.orig), "danger")
	return redirect(request.url)


@errors_bp.app_errorhandler(403)
def forbidden(error: HTTPException):
	return render_template("errors/forbidden.html"), 403


@errors_bp.app_errorhandler(404)
def not_found(error: HTTPException):
	return render_template("errors/not-found.html"), 404


@errors_bp.app_errorhandler(405)
def method_not_allowed(error: HTTPException):
	return render_template("errors/method-not-allowed.html"), 405


@errors_bp.app_errorhandler(500)
def internal_server(error: HTTPException):
	db.session.rollback()
	return render_template("errors/internal-server.html"), 500
