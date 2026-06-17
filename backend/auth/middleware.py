from functools import wraps
from typing import Any, Callable

from flask import g, jsonify, redirect, request, session

from backend.auth.service import AuthenticationError, decode_token


PUBLIC_API_PATHS = {
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/refresh",
    "/api/admin/auth/login",
    "/health",
}

PUBLIC_VIEW_PATHS = {
    "/login",
    "/admin/login",
    "/health",
}


def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def set_current_user_from_request() -> None:
    g.current_user = None

    session_user_id = session.get("user_id")
    session_username = session.get("external_username")
    if session_user_id:
        g.current_user = {
            "id": session_user_id,
            "external_username": session_username,
        }
        return

    token = _extract_bearer_token()
    if not token:
        return

    try:
        payload = decode_token(token, expected_type="access")
    except AuthenticationError:
        return
    except Exception:
        return

    g.current_user = {
        "id": payload["sub"],
        "external_username": payload.get("username"),
    }


def _is_public_path(path: str) -> bool:
    return path in PUBLIC_API_PATHS or path in PUBLIC_VIEW_PATHS


def register_auth_guards(app) -> None:
    @app.before_request
    def auth_first_guard() -> Any:
        set_current_user_from_request()
        path = request.path

        if _is_public_path(path) or path.startswith("/static/"):
            return None

        # Admin session bypasses normal user auth for /admin/* and /api/admin/* paths
        if session.get("is_admin") and (path.startswith("/admin") or path.startswith("/api/admin")):
            return None

        if path.startswith("/admin"):
            return redirect("/admin/login?reason=admin_required")

        if path.startswith("/api/admin") and path != "/api/admin/auth/login":
            return jsonify({"error": "Admin session required"}), 403

        if path.startswith("/api/") and not g.current_user:
            return jsonify({"error": "Unauthorized"}), 401

        if not path.startswith("/api/") and not g.current_user:
            return redirect("/login")

        return None


def auth_required() -> Callable:
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.current_user:
                return jsonify({"error": "Unauthorized"}), 401
            return fn(*args, **kwargs)

        return wrapper

    return decorator
