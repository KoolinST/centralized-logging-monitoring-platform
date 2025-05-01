# from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import os
from itsdangerous import URLSafeTimedSerializer
from flask import current_app


def get_serializer(expiration=3600):
    """Returns a serializer with the given expiration time."""
    salt = os.getenv("EMAIL_CONFIRM_SALT", "email-confirm-salt")
    return URLSafeTimedSerializer(
        secret_key=current_app.config["SECRET_KEY"], salt=salt
    )
