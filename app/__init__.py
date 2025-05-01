from flask import Flask
from dotenv import load_dotenv
from datetime import timedelta
from app.extensions import db, login_manager, bcrypt, mail, oauth
from app.routes.auth import auth
from app.routes.dashboard import dashboard
from app.routes.password import password
import os

load_dotenv()


def create_app():
    # App initialization
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static",
    )
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

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.remember_cookie_duration = timedelta(hours=1)

    # Register Blueprints
    app.register_blueprint(auth)
    app.register_blueprint(dashboard)
    app.register_blueprint(password)

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
