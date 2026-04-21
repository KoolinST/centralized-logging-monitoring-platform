import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import timedelta

from flask import Flask, Response, render_template
from dotenv import load_dotenv
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.extensions import db, login_manager, bcrypt, mail, oauth

load_dotenv()


def create_app(env=None):
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )

    if not env:
        env = os.getenv("FLASK_ENV", "development")

    if env == "production":
        from app.config.settings import ProductionConfig

        ProductionConfig.validate()
        app.config.from_object(ProductionConfig())
    elif env == "testing":
        from app.config.settings import TestingConfig

        app.config.from_object(TestingConfig)
    else:
        from app.config.settings import DevelopmentConfig

        app.config.from_object(DevelopmentConfig)

    log_level = logging.INFO if env in ("production", "testing") else logging.DEBUG
    formatter = logging.Formatter(
        "%(asctime)s %(name)s.%(funcName)s [%(levelname)s] - %(message)s"
    )

    file_handler = RotatingFileHandler("app.log", maxBytes=10_000_000, backupCount=3)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)

    if env == "development":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

    app.logger.setLevel(log_level)

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    PrometheusMetrics(app)

    login_manager.login_view = "auth.login"
    login_manager.remember_cookie_duration = timedelta(hours=1)

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

    from app.routes.auth import auth
    from app.routes.dashboard import dashboard
    from app.routes.password import password
    from app.routes.admin import admin
    from app.routes.proxy import proxy

    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(password)
    app.register_blueprint(admin)
    app.register_blueprint(proxy)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.route("/metrics")
    def metrics_endpoint():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.route("/test")
    def test():
        return "OK", 200

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        _seed_admin(app)

    from flask_wtf.csrf import generate_csrf

    @app.context_processor
    def inject_csrf():
        return dict(csrf_token=generate_csrf)

    @app.context_processor
    def inject_base_url():
        return dict(base_url=os.getenv("APP_BASE_URL", "http://localhost:5050"))

    return app


def _seed_admin(app):
    """Create the first admin account from environment variables if none exists."""
    from app.models.user import User
    from sqlalchemy import select

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_name = os.getenv("ADMIN_NAME", "Admin")
    admin_username = os.getenv("ADMIN_USERNAME", "admin")

    if not admin_email or not admin_password:
        app.logger.warning(
            "ADMIN_EMAIL or ADMIN_PASSWORD not set — skipping admin seed."
        )
        return

    existing = db.session.scalar(select(User).where(User.email == admin_email.lower()))
    if existing:
        return

    from app.extensions import bcrypt

    hashed_pw = bcrypt.generate_password_hash(admin_password).decode("utf-8")
    admin_user = User(
        name=admin_name,
        username=admin_username,
        email=admin_email.lower(),
        password=hashed_pw,
        role="admin",
        confirmed=True,
        status="approved",
    )
    db.session.add(admin_user)
    db.session.commit()
    app.logger.info(f"Admin account seeded: {admin_email}")
