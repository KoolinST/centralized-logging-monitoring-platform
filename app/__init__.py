from flask import Flask, Response
from dotenv import load_dotenv
from datetime import timedelta
from app.extensions import db, login_manager, bcrypt, mail, oauth
from app.routes.auth import auth
from app.routes.dashboard import dashboard
from app.routes.password import password
import os
import logging
from logging.handlers import RotatingFileHandler
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

load_dotenv()


def create_app(env=None):
    # App initialization
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )

    log_level = logging.INFO if env in ("production", "testing") else logging.DEBUG

    formatter = logging.Formatter(
        "%(asctime)s %(name)s.%(funcName)s [%(levelname)s] - %(message)s"
    )

    file_handler = RotatingFileHandler("app.log", maxBytes=10_000_000, backupCount=3)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    if not env:
        env = os.getenv("FLASK_ENV", "development")

    if env == "production":
        from app.config.settings import ProductionConfig

        app.config.from_object(ProductionConfig)
    elif env == "testing":
        from app.config.settings import TestingConfig

        app.config.from_object(TestingConfig)
    else:
        from app.config.settings import DevelopmentConfig

        app.config.from_object(DevelopmentConfig)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    metrics = PrometheusMetrics(app)
    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.remember_cookie_duration = timedelta(hours=1)

    # Register Blueprints
    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(password)

    @app.route("/metrics")
    def metrics_endpoint():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    oauth.init_app(app)
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        access_token_url="https://oauth2.googleapis.com/token",
        access_token_params=None,
        authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
        authorize_params={"access_type": "offline", "prompt": "consent"},
        api_base_url="https://www.googleapis.com/oauth2/v1/",
        userinfo_endpoint="https://www.googleapis.com/oauth2/v3/userinfo",
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
    )

    from app.models.user import User

    globals()["User"] = User

    @app.before_request
    def create_tables_and_seed_data():
        if app.config["ENV"] == "development":
            db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app
