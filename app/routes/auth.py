import time
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
from sqlalchemy import select
from app.extensions import db, bcrypt, oauth
from app.models.user import User, AuditLog
from app.forms.register import RegisterForm
from app.forms.login import LoginForm
from app.forms.oauth import SetUpPassword
from app.utils import generating
from app.utils.email import (
    send_confirmation_email,
    send_admin_new_user_notification,
)
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

auth = Blueprint(
    "auth",
    __name__,
    template_folder="../../frontend/templates/auth",
    static_folder="../../frontend/static",
)


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
                    role="developer",
                    status="pending",
                )
                db.session.add(new_user)
                db.session.flush()
                AuditLog.log(
                    action="register",
                    user_id=new_user.id,
                    detail=f"New registration: {new_user.email}",
                    ip_address=request.remote_addr,
                )
                db.session.commit()
                session["pending_email"] = new_user.email
                send_confirmation_email(new_user)
                send_admin_new_user_notification(new_user)
                registration_success_counter.inc()
                flash(
                    "Registration successful! Please check your email "
                    "to confirm your account.",
                    "success",
                )
                return redirect(url_for("auth.email_confirmation"))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Registration failed: {str(e)}")
                flash("Registration failed. Please try again.", "danger")
                registration_failure_counter.inc()
                return redirect(url_for("auth.register"))
    return render_template("registration.html", form=form)


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
                    if not user.confirmed:
                        flash(
                            "Please confirm your email before logging in.",
                            "warning",
                        )
                        session["pending_mail"] = user.email
                        return redirect(url_for("auth.email_confirmation"))
                    login_user(user)
                    user.last_login = int(time.time())
                    AuditLog.log(
                        action="login",
                        user_id=user.id,
                        detail=f"User logged in: {user.email}",
                        ip_address=request.remote_addr,
                    )
                    db.session.commit()
                    login_counter.inc()
                    if user.is_pending:
                        return redirect(url_for("auth.pending"))
                    if user.is_rejected:
                        logout_user()
                        flash(
                            "Your account has been rejected. Contact an administrator.",
                            "danger",
                        )
                        return redirect(url_for("auth.login"))
                    return redirect(url_for("dashboard.dashboard_view"))
                else:
                    AuditLog.log(
                        action="login_failed",
                        detail=f"Failed login attempt for: {form.email.data.lower()}",
                        ip_address=request.remote_addr,
                    )
                    db.session.commit()
                    flash(
                        "Login unsuccessful. Please check your email and password.",
                        "danger",
                    )
                    login_failure_counter.inc()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Login error: {str(e)}")
                flash("An unexpected error occurred. Please try again.", "danger")
                login_failure_counter.inc()
    return render_template("login.html", form=form)


@auth.route("/pending")
@login_required
def pending():
    if current_user.is_approved:
        return redirect(url_for("dashboard.dashboard_view"))
    if current_user.is_rejected:
        logout_user()
        flash("Your account has been rejected. Contact an administrator.", "danger")
        return redirect(url_for("auth.login"))
    from app.forms.logout import LogoutForm

    form = LogoutForm()
    return render_template("pending.html", user=current_user, form=form)


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
            AuditLog.log(
                action="email_confirmed",
                user_id=user.id,
                detail=f"Email confirmed: {user.email}",
                ip_address=request.remote_addr,
            )
            db.session.commit()
            flash(
                "Your email has been confirmed. "
                "Your account is now pending admin approval.",
                "success",
            )
            email_confirmation_success_counter.inc()
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Email confirmation failed: {str(e)}")
            flash("An unexpected error occurred. Please try again later.", "danger")
            email_confirmation_failure_counter.inc()
            return redirect(url_for("auth.login"))


@auth.route("/email_confirmation")
def email_confirmation():
    with endpoint_latency.labels(endpoint="/email_confirmation").time():
        email = session.get("pending_email", "")
        return render_template("email_confirmation.html", email=email)


@auth.route("/resend_confirmation", methods=["POST"])
def resend_confirmation():
    with endpoint_latency.labels(endpoint="/resend_confirmation").time():
        try:
            email = session.get("pending_email", "") or request.form.get("email", "")
            if not email:
                flash("Session expired. Please try logging in again.", "warning")
                return redirect(url_for("auth.login"))
            stmt = select(User).where(User.email == email.lower())
            user = db.session.scalar(stmt)
            if not user:
                flash("No account found with that email.", "danger")
                return redirect(url_for("auth.email_confirmation"))
            if user.confirmed:
                flash("Account already confirmed. Please log in.", "info")
                return redirect(url_for("auth.login"))
            current_time = int(time.time())
            expiry = user.email_confirmation_expiry or 0
            if (current_time - expiry) > 3600:
                send_confirmation_email(user)
                email_confirmation_sends_success_counter.inc()
                flash("Confirmation email resent.", "success")
            else:
                email_confirmation_sends_failure_counter.inc()
                flash(
                    "Email already sent recently. Please wait before requesting again.",
                    "warning",
                )
            session["pending_email"] = email.lower()
            return redirect(url_for("auth.email_confirmation"))
        except Exception as e:
            db.session.rollback()
            email_confirmation_sends_failure_counter.inc()
            current_app.logger.error(f"Resend error: {str(e)}")
            flash("An unexpected error occurred. Please try again.", "danger")
            return redirect(url_for("auth.email_confirmation"))


@auth.route("/logout", methods=["POST"])
@login_required
def logout():
    with endpoint_latency.labels(endpoint="/logout").time():
        AuditLog.log(
            action="logout",
            user_id=current_user.id,
            detail=f"User logged out: {current_user.email}",
            ip_address=request.remote_addr,
        )
        db.session.commit()
        user_email = current_user.email
        logout_user()
        current_app.logger.info(f"User '{user_email}' logged out successfully.")
        flash("You have been logged out.", "info")
        return redirect(url_for("auth.login"))


@auth.route("/check-box", methods=["GET"])
def check_box():
    with endpoint_latency.labels(endpoint="/check-box").time():
        return render_template("check-box.html")


@auth.route("/registerL", methods=["GET"])
def register_land():
    with endpoint_latency.labels(endpoint="/registerL").time():
        return render_template("registrationLand.html")


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
            flash(
                "An unexpected error occurred during Google sign-up. Please try again.",
                "danger",
            )
            return redirect(url_for("auth.register_land"))


@auth.route("/register/google/authorized")
def google_register_authorized():
    with endpoint_latency.labels(endpoint="/register/google/authorized").time():
        try:
            oauth.google.authorize_access_token()
            nonce = session.get("nonce")
            if not nonce:
                flash("Session expired. Please try again.", "danger")
                return redirect(url_for("auth.register"))
            user_info = oauth.google.get("userinfo").json()
            email = user_info.get("email")
            name = user_info.get("name") or user_info.get("given_name") or "User"
            if not email:
                flash(
                    "Could not retrieve email from Google. Please try again.", "danger"
                )
                return redirect(url_for("auth.register"))
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
            current_app.logger.error(f"Google registration error: {str(e)}")
            flash(
                "An unexpected error occurred during Google sign-up. Please try again.",
                "danger",
            )
            return redirect(url_for("auth.register"))


@auth.route("/setup_password", methods=["GET", "POST"])
def setup_password():
    with endpoint_latency.labels(endpoint="/setup_password").time():
        email = session.get("oauth_email")
        name = session.get("oauth_name")
        if not email or not name:
            flash("Session expired or invalid. Please authenticate again.", "danger")
            return redirect(url_for("auth.register_land"))
        form = SetUpPassword()
        if form.validate_on_submit():
            try:
                stmt = select(User).where(User.username == form.username.data.lower())
                existing_user = db.session.scalar(stmt)
                if existing_user:
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
                    role="developer",
                    status="pending",
                )
                db.session.add(new_user)
                db.session.flush()
                AuditLog.log(
                    action="register_oauth",
                    user_id=new_user.id,
                    detail=f"New Google OAuth registration: {email}",
                    ip_address=request.remote_addr,
                )
                db.session.commit()
                send_admin_new_user_notification(new_user)
                registration_success_counter.inc()
                login_user(new_user)
                session.pop("oauth_email", None)
                session.pop("oauth_name", None)
                flash(
                    "Registration successful! Your account is pending admin approval.",
                    "success",
                )
                return redirect(url_for("auth.pending"))
            except Exception as e:
                db.session.rollback()
                registration_failure_counter.inc()
                current_app.logger.error(f"Error during OAuth account setup: {e}")
                flash(
                    "An unexpected error occurred during account setup. "
                    "Please try again.",
                    "danger",
                )
                return redirect(url_for("auth.register_land"))
    return render_template("oauth_set_up_password.html", form=form)
