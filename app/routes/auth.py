from flask import render_template, redirect, url_for, flash, Blueprint, session
from flask_login import login_user, current_user, logout_user, login_required
from app.models.user import User
from app.forms.register import RegisterForm
from app.forms.login import LoginForm
from app.utils.email import send_confirmation_email
from sqlalchemy import select
from app.forms.resend_confirmation import ResendConfirmationForm
from app.forms.oauth import SetUpPassword
import time
from app.utils import generating


from app.extensions import db, bcrypt, oauth

auth = Blueprint(
    "auth",
    __name__,
    template_folder="../../frontend/templates/auth",
    static_folder="../../frontend/static",
)


@auth.route("/test")
def test_template():
    return render_template("test.html")


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_view"))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        new_user = User(
            name=form.name.data,
            username=form.username.data,
            email=form.email.data.lower(),
            password=hashed_pw,
        )
        db.session.add(new_user)
        db.session.commit()
        send_confirmation_email(new_user)
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.email_confirmation"))
    return render_template("registration.html", form=form)


@auth.route("/confirm_email/<token>")
def confirm_email(token):
    user = User.verify_and_get_user_from_email_token(token)
    if user is None:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for("password.token_invalid"))
    user.confirm_email()
    flash("Your email has been confirmed. You can now log in.", "success")
    return redirect(url_for("auth.login"))


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_view"))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            stmt = select(User).where(User.email == form.email.data.lower())
            user = db.session.scalar(stmt)
            if user and user.check_password(form.password.data):
                login_user(user)
                user.last_login = int(time.time())
                db.session.commit()
                flash("You have been logged in.", "success")
                return redirect(url_for("dashboard.dashboard_view"))
            else:
                flash(
                    "Login Unsuccessful. Please check your email and password.",
                    "danger",
                )
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
    return render_template("login.html", form=form)


@auth.route("/email_confirmation")
def email_confirmation():
    return render_template("email_confirmation.html")


@auth.route("/resend_confirmation", methods=["GET", "POST"])
def resend_confirmation():
    form = ResendConfirmationForm()
    if form.validate_on_submit():
        stmt = select(User).where(User.email == form.email.data.lower())
        user = db.session.scalar(stmt)

        if user:
            if user.confirmed:
                flash("Account already confirmed. Please log in.", "info")
                return redirect(url_for("auth.login"))

            current_time = int(time.time())
            if (
                user.email_confirmation_expiry is None
                or (current_time - user.email_confirmation_expiry) > 3600
            ):
                send_confirmation_email(user)
                return redirect(url_for("auth.email_confirmation"))
            else:
                return redirect(url_for("password.token_invalid_email"))
        else:
            flash("No account found with that email.", "danger")
    return render_template("resend_confirmation.html", form=form)


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth.route("/check-box", methods=["GET"])
def check_box():
    return render_template("check-box.html")


@auth.route("/registerL", methods=["GET"])
def register_land():
    return render_template("registrationLand.html")


@auth.route("/register/google")
def register_google():
    session.clear()
    nonce = generating.generate_nonce()
    session["nonce"] = nonce
    redirect_uri = url_for("auth.google_register_authorized", _external=True)
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)


@auth.route("/register/google/authorized")
def google_register_authorized():
    try:
        token = oauth.google.authorize_access_token()

        nonce = session.get("nonce")

        if not nonce:
            flash("Nonce missing. Please try again.", "danger")
            return redirect(url_for("auth.register"))

        resp = oauth.google.get("userinfo")
        user_info = resp.json()

        email = user_info.get("email")
        name = user_info.get("name") or user_info.get("given_name") or "User"

        stmt = select(User).where(User.email == email.lower())
        user = db.session.scalar(stmt)

        if user:
            flash(
                "An account with this email already exists. Please log in.", "warning"
            )
            return redirect(url_for("auth.login"))
        else:
            session["oauth_email"] = email
            session["oauth_name"] = name
            return redirect(url_for("auth.setup_password"))

    except Exception as e:
        flash(f"An error occurred during Google registration: {str(e)}", "danger")
        return redirect(url_for("auth.register"))


@auth.route("/setup_password", methods=["GET", "POST"])
def setup_password():
    form = SetUpPassword()

    email = session.get("oauth_email")
    name = session.get("oauth_name")

    if not email or not name:
        flash("Session expired or invalid. Please authenticate again.", "danger")
        return redirect(url_for("auth.login"))

    if form.validate_on_submit():
        existing_user = select(User).where(User.username == form.username.data)
        user = db.session.scalar(existing_user)
        if user:
            flash("Username already registered.", "warning")
            return render_template("oauth_set_up_password.html", form=form)

        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        new_user = User(
            name=name,
            username=form.username.data,
            email=email,
            password=hashed_pw,
            confirmed=True,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        flash("Registration successful. You are now logged in.", "success")
        session.pop("oauth_email", None)
        session.pop("oauth_name", None)

        return redirect(url_for("dashboard.dashboard_view"))

    return render_template("oauth_set_up_password.html", form=form)
