from flask import render_template, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user, logout_user
from app.forms.logout import LogoutForm
import time

dashboard = Blueprint(
    "dashboard",
    __name__,
    template_folder="../../frontend/templates/dashboard",
    static_folder="../../frontend/static",
)


@dashboard.route("/")
@dashboard.route("/dashboard")
@login_required
def dashboard_view():
    if (
        not current_user.last_login or time.time() - current_user.last_login > 3600
    ):
        logout_user()
        flash("Your session has expired. Please log in again.", "info")
        return redirect(url_for("auth.login"))

    form = LogoutForm()

    return render_template("dashboard.html", user=current_user, form=form)
