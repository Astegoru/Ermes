from flask import Blueprint, current_app, g, jsonify, request, session

from backend.admin.service import get_user_role
from backend.auth.middleware import auth_required
from backend.auth.service import AuthenticationError, decode_token, issue_tokens, login_with_facts
from backend.db.repositories import RepositoryError

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    try:
        result = login_with_facts(current_app.extensions["repo"], username=username, password=password)
        session["user_id"] = result["user"]["id"]
        session["external_username"] = result["user"]["external_username"]
        return jsonify(result), 200
    except AuthenticationError as exc:
        return jsonify({"error": str(exc)}), 401
    except RepositoryError as exc:
        return jsonify({"error": str(exc)}), 500


@bp.post("/refresh")
def refresh():
    payload = request.get_json(silent=True) or {}
    refresh_token = payload.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "refresh_token is required"}), 400

    try:
        token_payload = decode_token(refresh_token, expected_type="refresh")
        repo = current_app.extensions["repo"]
        user = repo.get_user_by_id(token_payload["sub"])
        return jsonify(issue_tokens(user)), 200
    except Exception:
        return jsonify({"error": "Invalid refresh token"}), 401


@bp.get("/me")
@auth_required()
def me():
    repo = current_app.extensions["repo"]
    user = repo.get_user_by_id(g.current_user["id"])
    role = get_user_role(repo, user["id"])
    return jsonify(
        {
            "id": user["id"],
            "external_username": user["external_username"],
            "display_name": user.get("display_name"),
            "is_active": user.get("is_active", True),
            "role": role,
        }
    )


@bp.get("/notifications")
@auth_required()
def list_notifications():
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    repo = current_app.extensions["repo"]
    rows = repo.list_notifications(g.current_user["id"], unread_only=unread_only)
    return jsonify(rows), 200


@bp.post("/notifications/<int:notification_id>/read")
@auth_required()
def mark_notification_read(notification_id: int):
    repo = current_app.extensions["repo"]
    try:
        row = repo.mark_notification_read(notification_id, g.current_user["id"])
    except RepositoryError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(row), 200


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True}), 200
