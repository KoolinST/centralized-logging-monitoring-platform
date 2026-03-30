import time
from app.extensions import db, bcrypt
from flask_login import UserMixin
from app.utils.token import get_serializer


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    username = db.Column(db.String(16), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(74), unique=True, nullable=False)

    role = db.Column(db.String(20), default="developer")

    confirmed = db.Column(db.Boolean, default=False)

    status = db.Column(db.String(20), default="pending")
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    approved_at = db.Column(db.Integer, nullable=True)

    last_login = db.Column(db.Integer, default=lambda: int(time.time()))

    password_reset_token = db.Column(db.String(128), nullable=True)
    password_reset_used = db.Column(db.Boolean, default=False)
    password_reset_expiry = db.Column(db.Integer, nullable=True)

    email_confirmation_token = db.Column(db.String(128), nullable=True)
    email_confirmation_expiry = db.Column(db.Integer, nullable=True)

    audit_logs = db.relationship(
        "AuditLog",
        foreign_keys="AuditLog.user_id",
        backref="user",
        lazy=True,
    )

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_developer(self):
        return self.role == "developer"

    @property
    def is_viewer(self):
        return self.role == "viewer"

    @property
    def is_approved(self):
        return self.status == "approved"

    @property
    def is_pending(self):
        return self.status == "pending"

    @property
    def is_rejected(self):
        return self.status == "rejected"

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def get_reset_token(self):
        s = get_serializer()
        token = s.dumps({"type": "password_reset", "reset_user_id": self.id})
        self.password_reset_token = token
        self.password_reset_expiry = int(time.time())
        return token

    @staticmethod
    def verify_and_get_user_from_reset_token(token, max_age=1800):
        s = get_serializer()
        try:
            data = s.loads(token, max_age=max_age)
            if data.get("type") != "password_reset":
                return None
            user_id = data.get("reset_user_id")
            if user_id is None:
                return None
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    def invalidate_reset_token(self):
        self.password_reset_used = True
        self.password_reset_token = None

    def reset_password_reset_status(self):
        self.password_reset_used = False
        self.password_reset_token = None
        self.password_reset_expiry = None

    def get_email_confirmation_token(self):
        s = get_serializer()
        token = s.dumps({"type": "email_confirmation", "confirm_user_id": self.id})
        self.email_confirmation_token = token
        self.email_confirmation_expiry = int(time.time())
        return token

    @staticmethod
    def verify_and_get_user_from_email_token(token, max_age=86400):
        s = get_serializer()
        try:
            data = s.loads(token, max_age=max_age)
            if data.get("type") != "email_confirmation":
                return None
            user_id = data.get("confirm_user_id")
            if user_id is None:
                return None
            return db.session.get(User, int(user_id))
        except Exception:
            return None

    def confirm_email(self):
        self.confirmed = True
        self.email_confirmation_token = None
        self.email_confirmation_expiry = None


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    action = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.String(256), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    timestamp = db.Column(db.Integer, default=lambda: int(time.time()))

    @staticmethod
    def log(action, user_id=None, detail=None, ip_address=None):
        entry = AuditLog(
            user_id=user_id,
            action=action,
            detail=detail,
            ip_address=ip_address,
        )
        db.session.add(entry)
