import time
from flask import (
    current_app,
    render_template,
    redirect,
    url_for,
    flash,
    Blueprint,
    request,
)
from flask_login import login_required, current_user
from sqlalchemy import select
from app.extensions import db
from app.models.user import User, AuditLog
from app.utils.decorators import admin_required
from app.utils.email import send_approval_email, send_rejection_email
from app.metrics import endpoint_latency

admin = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../../frontend/templates/admin",
    static_folder="../../frontend/static",
)


@admin.route("/")
@login_required
@admin_required
def dashboard():
    with endpoint_latency.labels(endpoint="/admin").time():
        pending_users = db.session.scalars(
            select(User).where(User.status == "pending")
        ).all()
        all_users = db.session.scalars(
            select(User).where(User.id != current_user.id).order_by(User.id)
        ).all()
        recent_logs = db.session.scalars(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50)
        ).all()
        return render_template(
            "admin_dashboard.html",
            pending_users=pending_users,
            all_users=all_users,
            recent_logs=recent_logs,
            user=current_user,
        )


@admin.route("/approve/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def approve_user(user_id):
    with endpoint_latency.labels(endpoint="/admin/approve").time():
        try:
            user = db.session.get(User, user_id)
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))
            if user.status == "approved":
                flash(f"{user.email} is already approved.", "info")
                return redirect(url_for("admin.dashboard"))
            user.status = "approved"
            user.approved_by = current_user.id
            user.approved_at = int(time.time())
            AuditLog.log(
                action="user_approved",
                user_id=current_user.id,
                detail=f"Admin {current_user.email} approved {user.email}",
                ip_address=request.remote_addr,
            )
            db.session.commit()
            send_approval_email(user)
            flash(f"{user.email} has been approved.", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while approving the user.", "danger")
            current_app.logger.error(f"Approve error: {str(e)}")
        return redirect(url_for("admin.dashboard"))


@admin.route("/reject/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def reject_user(user_id):
    with endpoint_latency.labels(endpoint="/admin/reject").time():
        try:
            user = db.session.get(User, user_id)
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))
            if user.status == "rejected":
                flash(f"{user.email} is already rejected.", "info")
                return redirect(url_for("admin.dashboard"))
            user.status = "rejected"
            AuditLog.log(
                action="user_rejected",
                user_id=current_user.id,
                detail=f"Admin {current_user.email} rejected {user.email}",
                ip_address=request.remote_addr,
            )
            db.session.commit()
            send_rejection_email(user)
            flash(f"{user.email} has been rejected.", "warning")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while rejecting the user.", "danger")
            current_app.logger.error(f"Reject error: {str(e)}")
        return redirect(url_for("admin.dashboard"))


@admin.route("/role/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def change_role(user_id):
    with endpoint_latency.labels(endpoint="/admin/role").time():
        try:
            user = db.session.get(User, user_id)
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))
            new_role = request.form.get("role")
            if new_role not in ("admin", "developer", "viewer"):
                flash("Invalid role.", "danger")
                return redirect(url_for("admin.dashboard"))
            old_role = user.role
            user.role = new_role
            AuditLog.log(
                action="role_changed",
                user_id=current_user.id,
                detail=f"Admin {current_user.email} changed "
                f"{user.email} role: {old_role} to {new_role}",
                ip_address=request.remote_addr,
            )
            db.session.commit()
            flash(f"{user.email} role changed to {new_role}.", "success")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while changing the role.", "danger")
            current_app.logger.error(f"Role change error: {str(e)}")
        return redirect(url_for("admin.dashboard"))


@admin.route("/deactivate/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def deactivate_user(user_id):
    with endpoint_latency.labels(endpoint="/admin/deactivate").time():
        try:
            user = db.session.get(User, user_id)
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("admin.dashboard"))
            if user.id == current_user.id:
                flash("You cannot deactivate your own account.", "danger")
                return redirect(url_for("admin.dashboard"))
            user.status = "rejected"
            AuditLog.log(
                action="user_deactivated",
                user_id=current_user.id,
                detail=f"Admin {current_user.email} deactivated {user.email}",
                ip_address=request.remote_addr,
            )
            db.session.commit()
            flash(f"{user.email} has been deactivated.", "warning")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while deactivating the user.", "danger")
            current_app.logger.error(f"Deactivate error: {str(e)}")
        return redirect(url_for("admin.dashboard"))


@admin.route("/audit")
@login_required
@admin_required
def audit_log():
    with endpoint_latency.labels(endpoint="/admin/audit").time():
        logs = db.session.scalars(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200)
        ).all()
        return render_template("audit_log.html", logs=logs, user=current_user)
