import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(hours=1)

    # Mail
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    TEMPLATES_AUTO_RELOAD = True

    @classmethod
    def validate(cls):
        required = [
            "SECRET_KEY",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "MAIL_DEFAULT_SENDER",
        ]
        missing = [key for key in required if not os.getenv(key)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


class DevelopmentConfig(Config):
    ENV = "development"
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    ENV = "production"
    DEBUG = False

    @classmethod
    def validate(cls):
        super().validate()
        required_prod = ["DATABASE_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]
        missing = [key for key in required_prod if not os.getenv(key)]
        if missing:
            raise EnvironmentError(
                f"Missing required production environment variables: "
                f"{', '.join(missing)}"
            )

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        uri = os.getenv("DATABASE_URL")
        if not uri:
            raise EnvironmentError(
                "DATABASE_URL must be set in production, "
                "refusing to fall back to SQLite."
            )
        return uri


class TestingConfig(Config):
    ENV = "testing"
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    SECRET_KEY = "test-secret-key"
