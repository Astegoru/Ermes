from flask import Blueprint, current_app, jsonify, request, session

from backend.admin.service import VALID_ROLES, validate_admin_credentials

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


@bp.get("/users")
def list_users():
    if not _admin_required():
        return jsonify({"error": "Forbidden"}), 403

    repo = current_app.extensions["repo"]
    users = repo.list_users()
    user_ids = [item["id"] for item in users]
    profiles = repo.list_user_profiles(user_ids)
    profile_map = {item["user_id"]: item for item in profiles}

    for user in users:
        profile = profile_map.get(user["id"], {})
        user["role"] = profile.get("role", "outsider")
        user["profiled_by"] = profile.get("profiled_by")
        user["profile_updated_at"] = profile.get("updated_at")

    return jsonify(users), 200


@bp.post("/users/<user_id>/profile")
def profile_user(user_id: str):
    if not _admin_required():
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    role = (payload.get("role") or "").strip().lower()
    if role not in VALID_ROLES:
        return jsonify({"error": "role must be one of moneda, solver, outsider"}), 400

    repo = current_app.extensions["repo"]
    row = repo.upsert_user_profile(
        user_id=user_id,
        role=role,
        profiled_by=payload.get("profiled_by") or "admin",
    )
    return jsonify(row), 200
