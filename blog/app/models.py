from __future__ import annotations

import secrets
from io import BytesIO
from datetime import datetime
from typing import Any, List, Dict, Union, Tuple

import pyotp
import pyqrcode
import sqlalchemy as sa
from flask import session, current_app, has_request_context
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from werkzeug.utils import cached_property
from werkzeug.datastructures import FileStorage
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy_utils import ScalarListType

from . import db
from .config import BaseConfig


class BaseModel(db.Model):
	__abstract__ = True

	id = db.Column(db.Integer, primary_key=True)
	created_at = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
	updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

	def __repr__(self) -> str:
		return "<%s id=%d>" % (self.__class__.__name__, self.id)


class _OnlineMixin:
	"""Initially, I made the attributes below only for `Session` model
	and in the `User` model found the last used session and get all the
	online information from him. However, I later realized that users
	couldn't have sessions due to, for example, logging out of the account.
	So, I have to use this."""

	last_online = db.Column(db.DateTime, default=datetime.utcnow)

	@property
	def is_online(self) -> bool:
		last_online_ago = datetime.utcnow() - self.last_online
		return last_online_ago.seconds <= 10


class User(_OnlineMixin, BaseModel):
	image_filename = db.Column(db.String(40), default=BaseConfig.DEFAULT_USER_IMAGE_FILENAME)
	email = db.Column(db.String(60), unique=True, index=True, nullable=False)
	username = db.Column(db.String(30), unique=True, index=True, nullable=False)
	password_hash = db.Column(db.String(255))
	information = db.Column(db.Text)
	location = db.Column(db.String(50))
	warnings = db.Column(db.Integer, default=0)
	backup_code_hashes = db.Column(MutableList.as_mutable(ScalarListType))
	secret_key = db.Column(db.String(16), unique=True, index=True,
   						default=pyotp.random_base32, nullable=False)
	email_is_confirmed = db.Column(db.Boolean, default=False)
	totp_is_enabled = db.Column(db.Boolean, default=False)
	is_receiving_notifications = db.Column(db.Boolean, default=True)
	is_active = db.Column(db.Boolean, default=True)
	is_staff = db.Column(db.Boolean, default=False)

	def __repr__(self) -> str:
		return "<User email=\"%s\">" % self.email

	@staticmethod
	def _on_changed_email(target: User, value: str, old_value: str, *args: Any) -> str:
		value = value.lower()
		if value != old_value:
			target.email_is_confirmed = False
		return value

	@staticmethod
	def _on_changed_warnings(target: User, value: int, *args: Any) -> None:
		max_count = current_app.config['USER_WARNINGS_MAX_COUNT']
		if value >= max_count and target.is_active and not target.is_staff:
			target.is_active = False

	@classmethod
	def _on_changed_totp_is_enabled(cls, target: User, value: bool, *args: Any) -> None:
		if not value:
			target.secret_key = pyotp.random_base32()

	@property
	def is_authenticated(self) -> bool:
		"""It requires `flask_login`"""
		return True

	@property
	def is_anonymous(self) -> bool:
		"""It requires `flask_login`"""
		return False

	@property
	def image_is_default(self) -> bool:
		return self.image_filename == current_app.config['DEFAULT_USER_IMAGE_FILENAME']

	@property
	def has_active_mail_token(self) -> bool:
		if self.mail_token is not None:
			if not self.mail_token.expired:
				return True
			db.session.delete(self.mail_token)
			db.session.commit()
		return False

	@cached_property
	def action_logs(self) -> Dict[datetime, str]:
		assert hasattr(current_app, "action_logger")

		response = current_app.action_logger.hgetall(self.id)  # type: ignore
		logs = {datetime.utcfromtimestamp(float(ts)): msg for ts, msg in response.items()}
		return dict(reversed(list(logs.items())))  # First the newest

	def get_id(self) -> int:
		"""It requires `flask_login`"""
		return self.id

	def log_action(self, message: str, /) -> None:
		if hasattr(current_app, "action_logger"):
			ts = datetime.utcnow().timestamp()
			current_app.action_logger.hset(self.id, ts, message)  # type: ignore

	def has_oauth_bind(self, provider: str) -> bool:
		return self.oauths.filter_by(provider=provider).first() is not None

	def set_password(self, password: str, /) -> None:
		self.password_hash = generate_password_hash(password, "sha256")

	def check_password(self, password: str, /) -> bool:
		if self.password_hash is None:
			return False
		return check_password_hash(self.password_hash, password)

	def set_image(self, image: Union[FileStorage, BytesIO], /) -> None:
		if not self.image_is_default:
			delete_image(self.image_filename)
		self.image_filename = save_image(image)

	def check_current_totp(self, code: str) -> bool:
		totp = pyotp.TOTP(self.secret_key)
		return totp.verify(code)

	def get_totp_qrcode(self) -> pyqrcode.QRCode:
		issuer_name = current_app.config['TOTP_ISSUER_NAME']

		totp = pyotp.TOTP(self.secret_key)
		totp_uri = totp.provisioning_uri(name=self.email, issuer_name=issuer_name)

		return pyqrcode.create(totp_uri)

	def genset_backup_codes(self) -> List[str]:
		"""Generates backup codes that are later hashed and written
		to the database.

		:return: Generated codes before hashing
		"""

		assert self.totp_is_enabled, ("Generation of backup codes makes"
  									" no sense if TOTP is disabled.")

		codes = [secrets.token_hex(4).upper() for _ in range(4)]
		self.backup_code_hashes = [
			generate_password_hash(c, method="sha1") for c in codes
		]

		return codes

	def check_backup_code(self, code: str, /) -> bool:
		return any(check_password_hash(h, code) for h in self.backup_code_hashes)

	def delete_backup_code(self, code: str, /) -> None:
		for code_hash in self.backup_code_hashes:
			if check_password_hash(code_hash, code):
				self.backup_code_hashes.remove(code_hash)
				return

		raise KeyError("This backup code doesn't exist.")

	def create_active_mail_token(self, type_: str) -> MailToken:
		rv = MailToken(owner=self, type=type_)
		db.session.add(rv)

		return rv

	def send_notification(self, text: str, /) -> Notification:
		rv = Notification(recipient=self, text=text)
		db.session.add(rv)

		return rv


db.event.listen(User.email, "set", User._on_changed_email, retval=True)
db.event.listen(User.warnings, "set", User._on_changed_warnings)
db.event.listen(User.totp_is_enabled, "set", User._on_changed_totp_is_enabled)


class Session(_OnlineMixin, BaseModel):
	key = db.Column(db.String(36), index=True, unique=True)
	data = db.Column(db.LargeBinary, nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	user = db.relationship("User", backref=db.backref(
		"sessions", cascade="all,delete", lazy="dynamic",
	))
	agent = db.Column(db.String(255), nullable=False)
	expires_at = db.Column(db.DateTime, index=True, nullable=False)

	def __repr__(self) -> str:
		args = ["key=\"%s\"" % self.key]
		if self.user is not None:
			args.append("user.email=\"%s\"" % self.user.email)
		return "<Session %s>" % ", ".join(args)

	@staticmethod
	def _before_delete(mapper: sa.orm.Mapper,
   					connection: sa.engine.Connection,
   					target: Session) -> None:
		if has_request_context():
			if target.key == session.key:  # type: ignore
				raise ValueError("We can't terminate a current session.")

	@property
	def expired(self) -> bool:
		return datetime.utcnow() > self.expires_at


db.event.listen(Session, "before_delete", Session._before_delete)


class OAuth(OAuthConsumerMixin, BaseModel):
	__table_args__ = (db.UniqueConstraint("social_id", "provider"),)

	social_id = db.Column(db.String(255), index=True, nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	user = db.relationship("User", backref=db.backref(
		"oauths", cascade="all,delete", lazy="dynamic",
	))


class MailToken(BaseModel):
	EMAIL_CONFIRM_TYPE = "email_confirm"
	PASSWORD_RESET_TYPE = "password_reset"

	owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	owner = db.relationship("User", backref=db.backref(
		"mail_token", cascade="all,delete", uselist=False,
	))
	key = db.Column(db.String(10), unique=True, nullable=False,
					index=True, default=lambda: secrets.token_hex(15))
	type = db.Column(db.String(30), nullable=False)
	expires_at = db.Column(db.DateTime, nullable=False, default=lambda: (
		datetime.utcnow() + current_app.config['MAIL_TOKENS_MAX_AGE']
	))

	def __repr__(self) -> str:
		info = (self.owner.email, self.key)
		return "<MailToken owner.email=\"%s\" key=\"%s\">" % info

	@classmethod
	def _on_changed_type(cls, target: MailToken, value: str, *args: Any) -> None:
		if value not in cls.get_types():
			raise ValueError("Invalid type.")

	@classmethod
	def get_types(cls) -> Tuple[str, ...]:
		return tuple(value for key, value in cls.__dict__.items()
 					if key.isupper() and key.endswith("_TYPE"))

	@property
	def expired(self) -> bool:
		return datetime.utcnow() > self.expires_at


db.event.listen(MailToken.type, "set", MailToken._on_changed_type)


class Notification(BaseModel):
	text = db.Column(db.Text, nullable=False)
	is_checked = db.Column(db.Boolean, default=False)
	recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	recipient = db.relationship("User", backref=db.backref(
		"notifications", cascade="all,delete", lazy="dynamic",
	))

	def __repr__(self) -> str:
		return "<Notification recipient.email=\"%s\">" % self.recipient.email

	@staticmethod
	def _on_changed_recipient(target: User, value: User, *args: Any) -> None:
		if not value.is_receiving_notifications:
			raise ValueError("User turned off receiving notifications.")


db.event.listen(Notification.recipient, "set", Notification._on_changed_recipient)


_post_tag = db.Table(
	"post_tag",
	db.Column("post_id", db.Integer, db.ForeignKey("post.id"), primary_key=True),
	db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Post(BaseModel):
	__table_args__ = (db.UniqueConstraint("title", "preview_text", "text"),)

	author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	author = db.relationship("User", backref=db.backref("posts", lazy="dynamic"))
	image_filename = db.Column(db.String(50), unique=True)
	title = db.Column(db.String(140), index=True, nullable=False)
	preview_text = db.Column(db.Text, nullable=False)
	text = db.Column(db.Text, nullable=False)
	slug = db.Column(db.String(175), unique=True, index=True, nullable=False)
	tags = db.relationship("Tag", secondary=_post_tag, lazy="dynamic",
   						backref=db.backref("posts", lazy="dynamic"))

	def __repr__(self) -> str:
		return "<Post title=\"%s\">" % self.title

	@staticmethod
	def _before_save(mapper: sa.orm.Mapper,
 					connection: sa.engine.Connection,
 					target: Post) -> None:
		if not target.slug:
			target.slug = generate_slug(target.title)

	@staticmethod
	def _before_delete(mapper: sa.orm.Mapper,
   					connection: sa.engine.Connection,
   					target: Post) -> None:
		if target.image_filename is not None:
			delete_image(target.image_filename)

	def set_image(self, image: Union[FileStorage, BytesIO], /) -> None:
		if self.image_filename is not None:
			delete_image(self.image_filename)
		self.image_filename = save_image(image)

	@classmethod
	def search(cls, query: str, /) -> db.Query:
		results_qs = cls.query.filter(
			cls.title.contains(query)
			| cls.preview_text.contains(query)
			| cls.text.contains(query)
			| cls.slug.contains(query)
		)
		return results_qs.order_by(cls.created_at.desc())

	def add_like(self, sender: User) -> PostLike:
		rv = PostLike(sender=sender, post=self)
		db.session.add(rv)

		return rv

	def check_like(self, sender: User) -> bool:
		return self.likes.filter_by(sender=sender).first() is not None

	def delete_like(self, sender: User) -> None:
		like = self.likes.filter_by(sender=sender).first()
		db.session.delete(like)

	def add_comment(self, text: str, /, author: User) -> PostComment:
		rv = PostComment(author=author, post=self, text=text)
		db.session.add(rv)

		return rv


for _e in ("before_insert", "before_update"):
	db.event.listen(Post, _e, Post._before_save)
db.event.listen(Post, "before_delete", Post._before_delete)


class PostLike(BaseModel):
	__table_args__ = (db.UniqueConstraint("sender_id", "post_id"),)

	sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	sender = db.relationship("User", backref=db.backref(
		"post_likes", cascade="all,delete", lazy="dynamic",
	))
	post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
	post = db.relationship("Post", backref=db.backref(
		"likes", cascade="all,delete", lazy="dynamic",
	))

	def __repr__(self) -> str:
		info = (self.sender_id, self.post_id)
		return "<PostLike sender_id=%d, post_id=%d>" % info


class PostComment(BaseModel):
	id = BaseModel.id  # For parent.remote_side vision
	text = db.Column(db.Text, nullable=False)
	author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
	author = db.relationship("User", backref=db.backref(
		"post_comments", cascade="all,delete", lazy="dynamic",
	))
	post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
	post = db.relationship("Post", backref=db.backref(
		"comments", cascade="all,delete", lazy="dynamic",
	))
	parent_id = db.Column(db.Integer, db.ForeignKey("post_comment.id"))
	parent = db.relationship("PostComment", remote_side=id, backref=db.backref(
		"replies", cascade="all,delete", lazy="dynamic",
	))

	def __repr__(self) -> str:
		info = (self.author.email, self.text)
		return "<PostComment author.email=\"%s\" text=\"%s\">" % info

	@property
	def was_updated(self) -> bool:
		return self.updated_at is not None

	@staticmethod
	def _on_changed_text(target: PostComment, value: str, *args: Any) -> str:
		return process_user_markdown(value)

	def add_reply(self, text: str, /, author: User) -> PostComment:
		new_reply = PostComment(author=author, parent=self,
								text=text, post=self.post)
		db.session.add(new_reply)

		return new_reply


db.event.listen(PostComment.text, "set", PostComment._on_changed_text, retval=True)


class Tag(BaseModel):
	name = db.Column(db.String(50), unique=True, index=True, nullable=False)

	def __repr__(self) -> str:
		return "<Tag name=\"%s\">" % self.name


# Circular imports
from .utils import save_image, delete_image, generate_slug, process_user_markdown
