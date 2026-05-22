from flask import Blueprint, current_app, jsonify, request, session

from backend.admin.service import validate_admin_credentials

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.post("/auth/login")
def admin_login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not validate_admin_credentials(username, password):
        return jsonify({"error": "Invalid admin credentials"}), 401

    session["is_admin"] = True
    return jsonify({"ok": True}), 200


def _admin_required() -> bool:
    return bool(session.get("is_admin"))


@bp.post("/superuser/assign")
def assign_superuser():
    if not _admin_required():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    repo = current_app.extensions["repo"]
    row = repo.assign_superuser(user_id=user_id, actor="admin")
    return jsonify(row), 200


@bp.get("/superuser")
def get_superuser():
    if not _admin_required():
        return jsonify({"error": "Forbidden"}), 403

    repo = current_app.extensions["repo"]
    row = repo.get_superuser()
    return jsonify(row or {"key": "superuser_id", "value": None}), 200
