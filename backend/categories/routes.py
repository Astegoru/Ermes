from flask import Blueprint, current_app, g, jsonify, request

from backend.auth.middleware import auth_required

bp = Blueprint("categories", __name__, url_prefix="/api/categories")


@bp.post("")
@auth_required()
def create_category():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    repo = current_app.extensions["repo"]
    created = repo.create_category(
        {
            "name": name,
            "description": payload.get("description"),
            "is_active": True,
            "merged_into_category_id": None,
            "created_by_user_id": g.current_user["id"],
        }
    )
    return jsonify(created), 201


@bp.get("")
@auth_required()
def list_categories():
    repo = current_app.extensions["repo"]
    return jsonify(repo.list_active_categories()), 200


@bp.patch("/<category_id>")
@auth_required()
def update_category(category_id: str):
    payload = request.get_json(silent=True) or {}
    allowed = {"name", "description", "is_active"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    repo = current_app.extensions["repo"]
    updated = repo.update_category(category_id, updates)
    return jsonify(updated), 200


@bp.post("/merge")
@auth_required()
def merge_categories():
    payload = request.get_json(silent=True) or {}
    source_ids = payload.get("source_ids") or []
    target_id = payload.get("target_id")

    if not source_ids or not target_id:
        return jsonify({"error": "source_ids and target_id are required"}), 400

    repo = current_app.extensions["repo"]
    merged = repo.merge_categories(source_ids=source_ids, target_id=target_id, actor_user_id=g.current_user["id"])
    return jsonify(merged), 200
