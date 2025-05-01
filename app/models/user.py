from app import db
from flask_login import UserMixin
from app.utils.token import get_serializer
from app import bcrypt
import time


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    username = db.Column(db.String(16), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(74), unique=True, nullable=False)
    role = db.Column(db.String(20), default="user")
    confirmed = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.Integer, default=lambda: int(time.time()))

    password_reset_token = db.Column(db.String(128), nullable=True)
    password_reset_used = db.Column(db.Boolean, default=False)
    password_reset_expiry = db.Column(db.Integer, nullable=True)

    email_confirmation_token = db.Column(db.String(128), nullable=True)
    email_confirmation_expiry = db.Column(db.Integer, nullable=True)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")
        db.session.commit()

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    # === PASSWORD RESET TOKENS ===
    def get_reset_token(self):
        s = get_serializer()
        token = s.dumps({"type": "password_reset", "reset_user_id": self.id})
        self.password_reset_token = token
        self.password_reset_expiry = int(time.time())
        db.session.commit()
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
            user = db.session.get(User, int(user_id))
            if (
                user
                and user.password_reset_expiry
                and (int(time.time()) - user.password_reset_expiry > max_age)
            ):
                return None
            return user
        except Exception:
            return None

    def invalidate_reset_token(self):
        self.password_reset_used = True
        self.password_reset_token = None
        db.session.commit()

    def reset_password_reset_status(self):
        self.password_reset_used = False
        self.password_reset_token = None
        self.password_reset_expiry = None
        db.session.commit()

    # === EMAIL CONFIRMATION TOKENS ===
    def get_email_confirmation_token(self):
        s = get_serializer()
        token = s.dumps({"type": "email_confirmation", "confirm_user_id": self.id})
        self.email_confirmation_token = token
        self.email_confirmation_expiry = int(time.time())
        db.session.commit()
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
            user = db.session.get(User, int(user_id))
            if (
                user
                and user.email_confirmation_expiry
                and (int(time.time()) - user.email_confirmation_expiry > max_age)
            ):
                return None
            return user
        except Exception:
            return None

    def confirm_email(self):
        self.confirmed = True
        self.email_confirmation_token = None
        self.email_confirmation_expiry = None
        db.session.commit()
