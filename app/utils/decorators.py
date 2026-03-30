from functools import wraps
from flask import redirect, url_for, flash, render_template
from flask_login import current_user


def approved_required(f):
    """Block access for users who are not approved yet."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.is_pending:
            return redirect(url_for("auth.pending"))
        if current_user.is_rejected:
            flash("Your account has been rejected. Contact an administrator.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Allow access only to admins."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            return render_template("errors/403.html"), 403
        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    """Allow access only to users with one of the specified roles."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.is_approved:
                return redirect(url_for("auth.pending"))
            if current_user.role not in roles:
                return render_template("errors/403.html"), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator
