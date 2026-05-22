from flask import Blueprint, current_app, g, jsonify, request

from backend.auth.middleware import auth_required
from backend.tickets.service import (
    AuthorizationError,
    enforce_open_or_superuser,
    enforce_owner_open_or_superuser,
    enforce_owner_or_superuser,
)
from backend.admin.service import is_superuser

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


@bp.post("")
@auth_required()
def create_ticket():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    category_id = payload.get("category_id")

    if not title or not category_id:
        return jsonify({"error": "title and category_id are required"}), 400

    repo = current_app.extensions["repo"]
    ticket = repo.create_ticket(
        {
            "title": title,
            "urgency": int(payload.get("urgency", 1)),
            "category_id": category_id,
            "link": payload.get("link"),
            "file_url": payload.get("file_url"),
            "file_type": payload.get("file_type"),
            "description": payload.get("description"),
            "owner_user_id": g.current_user["id"],
            "status": "open",
            "solved_at": None,
            "deleted_at": None,
        }
    )
    return jsonify(ticket), 201


@bp.get("")
@auth_required()
def list_tickets():
    sort = request.args.get("sort", "urgency")
    order = request.args.get("order", "desc")
    status_param = request.args.get("status")
    category_id = request.args.get("category_id")

    statuses = None
    status = None
    if status_param:
        parsed_statuses = [value.strip() for value in status_param.split(",") if value.strip()]
        if len(parsed_statuses) > 1:
            statuses = parsed_statuses
        elif len(parsed_statuses) == 1:
            status = parsed_statuses[0]

    repo = current_app.extensions["repo"]
    tickets = repo.list_tickets(
        sort_field=sort,
        sort_desc=order.lower() != "asc",
        status=status,
        statuses=statuses,
        category_id=category_id or None,
    )

    owner_ids = list({t["owner_user_id"] for t in tickets if t.get("owner_user_id")})
    if owner_ids:
        users = repo.get_users_by_ids(owner_ids)
        user_map = {u["id"]: u.get("external_username", "") for u in users}
        for ticket in tickets:
            ticket["owner_username"] = user_map.get(ticket["owner_user_id"], "")

    return jsonify(tickets), 200


@bp.get("/trash")
@auth_required()
def list_deleted_tickets():
    order = request.args.get("order", "desc")
    category_id = request.args.get("category_id")

    repo = current_app.extensions["repo"]
    can_view_all = is_superuser(repo, g.current_user["id"])
    owner_filter = None if can_view_all else g.current_user["id"]

    tickets = repo.list_deleted_tickets(
        sort_desc=order.lower() != "asc",
        category_id=category_id or None,
        owner_user_id=owner_filter,
    )

    owner_ids = list({t["owner_user_id"] for t in tickets if t.get("owner_user_id")})
    if owner_ids:
        users = repo.get_users_by_ids(owner_ids)
        user_map = {u["id"]: u.get("external_username", "") for u in users}
        for ticket in tickets:
            ticket["owner_username"] = user_map.get(ticket["owner_user_id"], "")

    return jsonify(tickets), 200


@bp.get("/<ticket_id>")
@auth_required()
def get_ticket(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    try:
        owner = repo.get_user_by_id(ticket["owner_user_id"])
        ticket["owner_username"] = owner.get("external_username") or ""
    except Exception:
        ticket["owner_username"] = ""

    try:
        category = repo.get_category(ticket["category_id"])
        ticket["category_name"] = category.get("name") or ""
    except Exception:
        ticket["category_name"] = ""

    if ticket.get("solved_by_user_id"):
        try:
            solver = repo.get_user_by_id(ticket["solved_by_user_id"])
            ticket["solved_by_username"] = solver.get("external_username") or ""
        except Exception:
            ticket["solved_by_username"] = ""

    return jsonify(ticket), 200


@bp.patch("/<ticket_id>")
@auth_required()
def edit_ticket(ticket_id: str):
    payload = request.get_json(silent=True) or {}
    allowed = {"title", "urgency", "category_id", "link", "description", "file_url", "file_type"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates:
        return jsonify({"error": "No valid fields to update"}), 400

    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    try:
        enforce_owner_open_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    updated = repo.update_ticket(ticket_id=ticket_id, updates=updates, actor_user_id=g.current_user["id"])
    return jsonify(updated), 200


@bp.post("/<ticket_id>/progress")
@auth_required()
def mark_in_progress(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    try:
        enforce_owner_open_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    if ticket.get("status") != "open":
        return jsonify({"error": "Ticket must be open to mark as in progress"}), 400

    updated = repo.mark_in_progress(ticket_id=ticket_id, actor_user_id=g.current_user["id"])
    return jsonify(updated), 200


@bp.post("/<ticket_id>/solve")
@auth_required()
def solve_ticket(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    try:
        enforce_open_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    solved = repo.solve_ticket(ticket_id=ticket_id, actor_user_id=g.current_user["id"])
    return jsonify(solved), 200


@bp.delete("/<ticket_id>")
@auth_required()
def delete_ticket(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    try:
        enforce_owner_open_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    deleted = repo.soft_delete_ticket(ticket_id=ticket_id, actor_user_id=g.current_user["id"])
    return jsonify(deleted), 200


@bp.post("/<ticket_id>/restore")
@auth_required()
def restore_ticket(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    if not ticket.get("deleted_at"):
        return jsonify({"error": "Ticket is not deleted"}), 400

    try:
        enforce_owner_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    restored = repo.restore_ticket(ticket_id=ticket_id, actor_user_id=g.current_user["id"])
    return jsonify(restored), 200


@bp.delete("/<ticket_id>/purge")
@auth_required()
def purge_ticket(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    if not ticket.get("deleted_at"):
        return jsonify({"error": "Ticket must be deleted before permanent removal"}), 400

    try:
        enforce_owner_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    deleted = repo.purge_ticket(ticket_id=ticket_id, actor_user_id=g.current_user["id"])
    return jsonify(deleted), 200
