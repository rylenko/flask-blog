from flask import abort, flash, url_for, request, redirect, current_app, render_template
from flask_babel import _
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict

from . import posts_bp
from .forms import PostForm, PostCommentForm
from .. import db
from ..models import Post, PostComment
from ..utils import get_next_url, flash_form_errors, check_rights_on_object
from ..decorators import (
	staff_required,
	email_confirmed_required,
	password_confirm_once_required,
)
from ..users.tasks import send_everyone_notification_task


@posts_bp.get("/")
def index():
	qs = Post.query.order_by(Post.created_at.desc())
	current_page = qs.paginate(per_page=current_app.config['POSTS_PER_PAGE'])

	return render_template("posts/index.html", page=current_page)


@posts_bp.get("/search/")
def search():
	query = request.args.get("query", type=str)

	if query is None:
		return render_template("posts/search.html")

	qs = Post.search(query)
	current_page = qs.paginate(per_page=current_app.config['POSTS_PER_PAGE'])
	return render_template("posts/search.html", query=query, page=current_page)


@posts_bp.route("/create/", methods=("GET", "POST"))
@login_required
@staff_required
@password_confirm_once_required
def create():
	if request.method == "POST":
		form_and_files = CombinedMultiDict((request.form, request.files))
		bound_form = PostForm(form_and_files)

		if bound_form.validate_on_submit():
			new_post = bound_form.populate()
			db.session.commit()

			flash(_("Your post was created successfully."), "success")
			send_everyone_notification_task.delay(render_template(
				"posts/notifications/new.html", post=new_post,
			))
			return redirect(url_for("posts.detail", slug=new_post.slug))

		return render_template("posts/create.html", form=bound_form)

	return render_template("posts/create.html", form=PostForm())


@posts_bp.get("/<slug>/")
def detail(slug: str):
	post = Post.query.filter_by(slug=slug).first_or_404()
	comments_qs = post.comments.order_by(PostComment.created_at.desc())
	comments_current_page = comments_qs.paginate(
		per_page=current_app.config['POST_COMMENTS_PER_PAGE'],
	)

	return render_template("posts/detail.html", comment_form=PostCommentForm(),
   						post=post, comments_page=comments_current_page)


@posts_bp.route("/<slug>/update/", methods=("GET", "POST"))
@login_required
@staff_required
@password_confirm_once_required
def update(slug: str):
	post = Post.query.filter_by(slug=slug).first_or_404()

	if request.method == "POST":
		form_and_files = CombinedMultiDict((request.form, request.files))  # type: ignore
		bound_form = PostForm(form_and_files, obj_on_update=post)

		if bound_form.validate_on_submit():
			bound_form.populate()
			flash(_("Your post was updated successfully."), "success")
			return redirect(url_for("posts.detail", slug=post.slug))

		return render_template("posts/update.html", form=bound_form)

	return render_template("posts/update.html", form=PostForm(obj=post))


@posts_bp.route("/<slug>/delete/", methods=("GET", "POST"))
@login_required
@staff_required
@password_confirm_once_required
def delete(slug: str):
	post = Post.query.filter_by(slug=slug).first_or_404()

	if request.method == "POST":
		db.session.delete(post)
		db.session.commit()
		flash(_("Your post was deleted successfully."), "success")
		return redirect(url_for("posts.index"))

	return render_template("posts/delete.html", post=post)


@posts_bp.post("/<slug>/like/")
@login_required
@email_confirmed_required
def like(slug: str):
	post = Post.query.filter_by(slug=slug).first_or_404()
	if post.check_like(sender=current_user):
		abort(403)

	post.add_like(sender=current_user)
	db.session.commit()

	flash(_("Your like was added successfully."), "success")
	return redirect(url_for("posts.detail", slug=post.slug))


@posts_bp.post("/<slug>/unlike/")
@login_required
@email_confirmed_required
def unlike(slug: str):
	post = Post.query.filter_by(slug=slug).first_or_404()
	if not post.check_like(sender=current_user):
		abort(403)

	post.delete_like(sender=current_user)
	db.session.commit()

	flash(_("Your like was deleted successfully."), "danger")
	return redirect(url_for("posts.detail", slug=post.slug))


@posts_bp.post("/<slug>/comment/")
@login_required
@email_confirmed_required
def comment(slug: str):
	post = Post.query.filter_by(slug=slug).first_or_404()
	bound_form = PostCommentForm(request.form)

	if bound_form.validate_on_submit():
		post.add_comment(bound_form.text.data, author=current_user)
		flash(_("Your comment was created successfully."), "success")
	else:
		flash_form_errors(bound_form)

	return redirect(url_for("posts.detail", slug=post.slug))


@posts_bp.post("/comments/<int:id>/reply/")
@login_required
@email_confirmed_required
def reply_comment(id: int):
	parent = PostComment.query.filter_by(id=id).first_or_404()
	bound_form = PostCommentForm(request.form)

	if bound_form.validate_on_submit():
		new_reply = parent.add_reply(bound_form.text.data, author=current_user)
		flash(_("Your reply was created successfully."), "success")

		if parent.author.is_receiving_notifications and new_reply.author != parent.author:
			parent.author.send_notification(render_template(
				"posts/comments/notifications/received-reply.html", comment=parent,
			))

		db.session.commit()
	else:
		flash_form_errors(bound_form)

	return redirect(url_for("posts.detail", slug=parent.post.slug))


@posts_bp.route("/comments/<int:id>/update/", methods=("GET", "POST"))
@login_required
@email_confirmed_required
def update_comment(id: int):
	comment = PostComment.query.get_or_404(id)
	if not check_rights_on_object(comment):
		abort(404)

	if request.method == "POST":
		bound_form = PostCommentForm(request.form)

		if bound_form.validate_on_submit():
			comment.text = bound_form.text.data
			db.session.commit()
			flash(_("Your comment was updated successfully."), "success")

			comment_post_link = url_for("posts.detail", slug=comment.post.slug)
			return redirect(get_next_url() or comment_post_link)

		return render_template("posts/comments/update.html", form=bound_form)

	return render_template("posts/comments/update.html", form=PostCommentForm(obj=comment))


@posts_bp.post("/comments/<int:id>/delete/")
@login_required
@email_confirmed_required
def delete_comment(id: int):
	comment = PostComment.query.get_or_404(id)
	if not check_rights_on_object(comment):
		abort(404)

	comment_post_slug = comment.post.slug
	db.session.delete(comment)
	db.session.commit()

	return redirect(url_for("posts.detail", slug=comment_post_slug))
