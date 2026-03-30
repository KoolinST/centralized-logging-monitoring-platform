from flask import Blueprint, redirect, request, make_response
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.models.user import AuditLog
from app.extensions import db

proxy = Blueprint("proxy", __name__, url_prefix="/proxy")


def _auth_check(service: str):
    """Return 200 if user is allowed, 403 if not."""
    if not current_user.is_authenticated:
        return make_response("Unauthorized", 401)
    if not current_user.is_approved:
        return make_response("Forbidden", 403)
    if current_user.role not in ("admin", "developer"):
        return make_response("Forbidden", 403)
    AuditLog.log(
        action=f"proxy_access_{service}",
        user_id=current_user.id,
        detail=f"{current_user.email} ({current_user.role}) accessed {service}",
        ip_address=request.headers.get("X-Real-IP", request.remote_addr),
    )
    db.session.commit()
    return make_response("OK", 200)


@proxy.route("/auth/kibana")
@login_required
def auth_kibana():
    return _auth_check("kibana")


@proxy.route("/auth/prometheus")
@login_required
def auth_prometheus():
    return _auth_check("prometheus")


@proxy.route("/auth/node-exporter")
@login_required
def auth_node_exporter():
    return _auth_check("node-exporter")


@proxy.route("/kibana")
@login_required
@role_required("admin", "developer")
def kibana():
    return redirect("http://localhost:8888/kibana/")


@proxy.route("/prometheus")
@login_required
@role_required("admin", "developer")
def prometheus():
    return redirect("http://localhost:8888/prometheus/")


@proxy.route("/node-exporter")
@login_required
@role_required("admin", "developer")
def node_exporter():
    return redirect("http://localhost:8888/node-exporter/")
