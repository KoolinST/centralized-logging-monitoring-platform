import time

from flask import render_template, redirect, url_for, flash, request, Blueprint
from flask_login import current_user
from sqlalchemy import select

from app.extensions import db, bcrypt
from app.models.user import User
from app.forms.updatePass import UpdatePasswordForm
from app.utils.email import send_reset_password

password = Blueprint(
    "password",
    __name__,
    template_folder="../../frontend/templates/password",
    static_folder="../../frontend/static",
)


@password.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not email:
            flash("Please enter your email address.", "warning")
            return render_template("forgot_password.html")

        try:
            stmt = select(User).where(User.email == email.lower())
            user = db.session.scalar(stmt)

            if not user:
                flash("No account found with that email address.", "danger")
                return render_template("forgot_password.html")

            if user.password_reset_expiry is not None:
                current_time = int(time.time())
                if (current_time - user.password_reset_expiry) <= 3600:
                    flash(
                        "You can request a new password reset email after 1 hour.",
                        "warning",
                    )
                    return render_template("forgot_password.html")

            user.reset_password_reset_status()
            db.session.commit()
            send_reset_password(user)
            return redirect(url_for("auth.check_box"))

        except Exception as e:
            db.session.rollback()
            from flask import current_app

            current_app.logger.error(f"Forgot password error for {email}: {str(e)}")
            flash("An unexpected error occurred. Please try again.", "danger")

    return render_template("forgot_password.html")


@password.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard_view"))

    user = User.verify_and_get_user_from_reset_token(token)
    if user is None:
        flash("That is an invalid or expired token.", "warning")
        return redirect(url_for("password.token_invalid"))

    if user.password_reset_used:
        flash("This token has already been used.", "warning")
        return redirect(url_for("password.token_invalid"))

    form = UpdatePasswordForm()

    if form.validate_on_submit():
        try:
            user.password = bcrypt.generate_password_hash(form.password.data).decode(
                "utf-8"
            )
            user.invalidate_reset_token()
            db.session.commit()
            flash("Your password has been updated!", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            from flask import current_app

            current_app.logger.error(
                f"Password reset failed for user {user.id}: {str(e)}"
            )
            flash("An unexpected error occurred. Please try again.", "danger")

    return render_template("reset_password.html", form=form, token=token)


@password.route("/token_invalid")
def token_invalid():
    return render_template("token_invalid.html")


@password.route("/token_invalid_email")
def token_invalid_email():
    return render_template("token_invalid_email.html")
