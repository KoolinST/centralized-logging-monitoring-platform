from flask import (
    render_template,
    redirect,
    url_for,
    flash,
    Blueprint,
    session,
    current_app,
    request,
)

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
from app.metrics import (
    registration_success_counter,
    registration_failure_counter,
    email_confirmation_failure_counter,
    email_confirmation_success_counter,
    email_confirmation_sends_success_counter,
    email_confirmation_sends_failure_counter,
    endpoint_latency,
    login_counter,
    login_failure_counter,
)


from app.extensions import db, bcrypt, oauth

auth = Blueprint(
    "auth",
    __name__,
    template_folder="../../frontend/templates/auth",
    static_folder="../../frontend/static",
)

# ---------------- TESTING ----------------


@auth.route("/test")
def test_template():
    current_app.logger.debug("Hello From test Roooute")
    return render_template("test.html")


# ---------------- REGISTER ----------------


@auth.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_view"))

    form = RegisterForm()
    with endpoint_latency.labels(endpoint="/register").time():
        if form.validate_on_submit():
            try:
                hashed_pw = bcrypt.generate_password_hash(form.password.data).decode(
                    "utf-8"
                )
                new_user = User(
                    name=form.name.data,
                    username=form.username.data.lower(),
                    email=form.email.data.lower(),
                    password=hashed_pw,
                )
                db.session.add(new_user)
                db.session.commit()
                send_confirmation_email(new_user)
                flash("Registration successful. Please log in.", "success")
                registration_success_counter.inc()
                return redirect(url_for("auth.email_confirmation"))
            except Exception as e:
                current_app.logger.error(f"Registration failed: {str(e)}")
                flash("Registration failed. Please try again.", "danger")
                registration_failure_counter.inc()
                return redirect(url_for("auth.register"))

    return render_template("registration.html", form=form)


# ---------------- LOGIN ----------------


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_view"))

    form = LoginForm()
    with endpoint_latency.labels(endpoint="/login").time():
        if form.validate_on_submit():
            try:
                stmt = select(User).where(User.email == form.email.data.lower())
                user = db.session.scalar(stmt)

                if user and user.check_password(form.password.data):
                    login_user(user)
                    user.last_login = int(time.time())
                    db.session.commit()
                    flash("You have been logged in.", "success")
                    login_counter.inc()
                    return redirect(url_for("dashboard.dashboard_view"))

                else:
                    flash(
                        "Login Unsuccessful. Please check your email and password.",
                        "danger",
                    )
                    login_failure_counter.inc()
            except Exception as e:
                current_app.logger.error(f"Login error: {str(e)}")
                flash(f"An error occurred: {str(e)}", "danger")
                login_failure_counter.inc()
    return render_template("login.html", form=form)


# ---------------- EMAIL CONFIRMATION ----------------


@auth.route("/confirm_email/<token>")
def confirm_email(token):
    with endpoint_latency.labels(endpoint="/confirm_email").time():
        try:
            user = User.verify_and_get_user_from_email_token(token)
            if user is None:
                flash("The confirmation link is invalid or has expired.", "danger")
                email_confirmation_failure_counter.inc()
                return redirect(url_for("password.token_invalid_email"))

            user.confirm_email()
            flash("Your email has been confirmed. You can now log in.", "success")
            email_confirmation_success_counter.inc()
            return redirect(url_for("auth.login"))

        except Exception as e:
            current_app.logger.error(f"Email confirmation failed: {str(e)}")
            flash("An unexpected error occurred. Please try again later.", "danger")
            email_confirmation_failure_counter.inc()
            return redirect(url_for("auth.login"))


@auth.route("/email_confirmation")
def email_confirmation():
    with endpoint_latency.labels(endpoint="/email_confirmation").time():
        current_app.logger.info(
            f"/email_confirmation accessed by {request.remote_addr}"
        )
        return render_template("email_confirmation.html")


@auth.route("/resend_confirmation", methods=["GET", "POST"])
def resend_confirmation():
    form = ResendConfirmationForm()
    with endpoint_latency.labels(endpoint="/resend_confirmation").time():
        if form.validate_on_submit():
            try:
                stmt = select(User).where(User.email == form.email.data.lower())
                user = db.session.scalar(stmt)
                if user:
                    if user.confirmed:
                        flash("Account already confirmed. Please log in.", "info")
                        current_app.logger.info(
                            f"Email already confirmed: {form.email.data.lower()}"
                        )
                        return redirect(url_for("auth.login"))

                    current_time = int(time.time())
                    expiry = user.email_confirmation_expiry or 0
                    if (current_time - expiry) > 3600:
                        send_confirmation_email(user)
                        email_confirmation_sends_success_counter.inc()
                        current_app.logger.info(
                            f"Resent confirmation to: {form.email.data.lower()}"
                        )
                        flash("Confirmation email resent.", "success")
                        return redirect(url_for("auth.email_confirmation"))
                    else:
                        email_confirmation_sends_failure_counter.inc()
                        flash(
                            "Confirmation email already sent recently. Please wait.",
                            "warning",
                        )
                        current_app.logger.warning(
                            f"Resend blocked (too soon): {form.email.data.lower()}"
                        )
                        return redirect(url_for("password.token_invalid_email"))
                else:
                    flash("No account found with that email.", "danger")
                    current_app.logger.warning(
                        f"Resend requested for "
                        f"nonexistent email: {form.email.data.lower()}"
                    )
            except Exception as e:
                email_confirmation_sends_failure_counter.inc()
                current_app.logger.error(
                    f"Resend error for {form.email.data.lower()}: {str(e)}"
                )
                flash(
                    "An error occurred while processing your "
                    "request. Please try again.",
                    "danger",
                )
    return render_template("resend_confirmation.html", form=form)


# ---------------- LOGOUT ----------------


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    with endpoint_latency.labels(endpoint="/logout").time():
        user_email = current_user.email
        logout_user()
        current_app.logger.info(f"User '{user_email}' logged out successfully.")
        flash("You have been logged out.", "info")
        return redirect(url_for("auth.login"))


# ---------------- STATIC PAGES ----------------


@auth.route("/check-box", methods=["GET"])
def check_box():
    with endpoint_latency.labels(endpoint="/check-box").time():
        return render_template("check-box.html")


@auth.route("/registerL", methods=["GET"])
def register_land():
    with endpoint_latency.labels(endpoint="/registerL").time():
        return render_template("registrationLand.html")


# ---------------- GOOGLE OAUTH ----------------


@auth.route("/register/google")
def register_google():
    with endpoint_latency.labels(endpoint="/register/google").time():
        try:
            session.clear()
            nonce = generating.generate_nonce()
            session["nonce"] = nonce
            redirect_uri = url_for("auth.google_register_authorized", _external=True)
            return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)
        except Exception as e:
            registration_failure_counter.inc()
            current_app.logger.error(f"Error during Google registration: {e}")
            flash(f"Error during Google registration: {e}", "danger")
            return redirect(url_for("auth.register_land"))


@auth.route("/register/google/authorized")
def google_register_authorized():
    with endpoint_latency.labels(endpoint="/register/google/authorized").time():
        try:
            token = oauth.google.authorize_access_token()
            nonce = session.get("nonce")

            if not nonce:
                flash("Nonce missing. Please try again.", "danger")
                return redirect(url_for("auth.register"))

            user_info = oauth.google.get("userinfo").json()
            email = user_info.get("email")
            name = user_info.get("name") or user_info.get("given_name") or "User"

            stmt = select(User).where(User.email == email.lower())
            user = db.session.scalar(stmt)

            if user:
                flash(
                    "An account with this email already exists. Please log in.",
                    "warning",
                )
                return redirect(url_for("auth.login"))

            session["oauth_email"] = email
            session["oauth_name"] = name
            return redirect(url_for("auth.setup_password"))

        except Exception as e:
            flash(f"An error occurred during Google registration: {str(e)}", "danger")
            current_app.logger.error(f"Google registration error: {str(e)}")
            return redirect(url_for("auth.register"))


# ---------------- SETUP PASSWORD ----------------


@auth.route("/setup_password", methods=["GET", "POST"])
def setup_password():
    with endpoint_latency.labels(endpoint="/setup_password").time():
        try:
            form = SetUpPassword()
            email = session.get("oauth_email")
            name = session.get("oauth_name")

            if not email or not name:
                flash(
                    "Session expired or invalid. Please authenticate again.", "danger"
                )
                return redirect(url_for("auth.register_land"))

            if form.validate_on_submit():
                existing_user = select(User).where(
                    User.username == form.username.data.lower()
                )
                user = db.session.scalar(existing_user)
                if user:
                    flash("Username already registered.", "warning")
                    return render_template("oauth_set_up_password.html", form=form)

                hashed_pw = bcrypt.generate_password_hash(form.password.data).decode(
                    "utf-8"
                )
                new_user = User(
                    name=name,
                    username=form.username.data.lower(),
                    email=email,
                    password=hashed_pw,
                    confirmed=True,
                )
                db.session.add(new_user)
                db.session.commit()
                current_app.logger.info(
                    f"User account created via setup_password: {email}"
                )
                registration_success_counter.inc()
                login_user(new_user)

                flash("Registration successful. You are now logged in.", "success")
                session.pop("oauth_email", None)
                session.pop("oauth_name", None)
                return redirect(url_for("dashboard.dashboard_view"))
        except Exception as e:
            registration_failure_counter.inc()
            current_app.logger.error(f"Error during Setup Password Registration: {e}")
            flash("Error during account setup.", "danger")
            return redirect(url_for("auth.registerL"))
    return render_template("oauth_set_up_password.html", form=form)
