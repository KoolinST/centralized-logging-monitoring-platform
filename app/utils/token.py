import os

from itsdangerous import URLSafeTimedSerializer
from flask import current_app


def get_serializer():
    salt = os.getenv("EMAIL_CONFIRM_SALT")
    if not salt:
        raise EnvironmentError(
            "EMAIL_CONFIRM_SALT must be set — refusing to use a default salt."
        )
    return URLSafeTimedSerializer(
        secret_key=current_app.config["SECRET_KEY"],
        salt=salt,
    )
