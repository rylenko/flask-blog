from flask import flash, url_for, request, redirect, current_app, render_template
from flask_babel import _
from flask_login import login_required

from . import tags_bp
from .forms import TagForm
from .. import db
from ..models import Tag, Post
from ..decorators import staff_required, password_confirm_once_required


@tags_bp.get("/")
def index():
	qs = Tag.query.order_by(Tag.name)
	current_page = qs.paginate(per_page=current_app.config['TAGS_PER_PAGE'])

	return render_template("tags/index.html", page=current_page)


@tags_bp.route("/create/", methods=("GET", "POST"))
@login_required
@staff_required
@password_confirm_once_required
def create():
	if request.method == "POST":
		bound_form = TagForm(request.form)

		if bound_form.validate_on_submit():
			new_tag = bound_form.populate()
			db.session.commit()

			flash(_("Your tag was created successfully."), "success")
			return redirect(url_for("tags.detail", name=new_tag.name))

		return render_template("tags/create.html", form=bound_form)

	return render_template("tags/create.html", form=TagForm())


@tags_bp.get("/<name>/")
def detail(name: str):
	tag = Tag.query.filter_by(name=name).first_or_404()
	posts_qs = tag.posts.order_by(Post.created_at.desc())
	posts_current_page = posts_qs.paginate(per_page=current_app.config['POSTS_PER_PAGE'])

	return render_template("tags/detail.html", tag=tag, posts_page=posts_current_page)


@tags_bp.route("/<name>/update/", methods=("GET", "POST"))
@login_required
@staff_required
@password_confirm_once_required
def update(name: str):
	tag = Tag.query.filter_by(name=name).first_or_404()

	if request.method == "POST":
		bound_form = TagForm(request.form, obj_on_update=tag)

		if bound_form.validate_on_submit():
			tag = bound_form.populate()
			db.session.commit()

			flash(_("Your tag was updated successfully."), "success")
			return redirect(url_for("tags.detail", name=tag.name))

		return render_template("tags/update.html", form=bound_form)

	return render_template("tags/update.html", form=TagForm(obj=tag))


@tags_bp.route("/<name>/delete/", methods=("GET", "POST"))
@login_required
@staff_required
@password_confirm_once_required
def delete(name: str):
	tag = Tag.query.filter_by(name=name).first_or_404()

	if request.method == "POST":
		db.session.delete(tag)
		db.session.commit()
		flash(_("Your tag was deleted successfully."), "success")
		return redirect(url_for("tags.index"))

	return render_template("tags/delete.html", tag=tag)
