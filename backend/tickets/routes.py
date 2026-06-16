import re
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request

from backend.auth.middleware import auth_required
from backend.admin.service import (
    VALID_ROLES,
    can_access_ticket_list,
    can_solve_ticket,
    is_superuser,
)
from backend.tickets.service import (
    AuthorizationError,
    enforce_open_or_superuser,
    enforce_owner_open_or_superuser,
    enforce_owner_or_superuser,
)
bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")

MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_.-]{2,64})")
VALID_COMMENT_MARKS = {"ticket", "sandwatch"}


def _extract_mentions(text: str) -> list[str]:
    return sorted({m.group(1) for m in MENTION_PATTERN.finditer(text or "")})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    if not can_access_ticket_list(repo, g.current_user["id"]):
        return jsonify({"error": "Only Moneda or Solver users can view the ticket list"}), 403

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

    if not can_access_ticket_list(repo, g.current_user["id"]):
        # Outsider users can only access their own tickets.
        if ticket.get("owner_user_id") != g.current_user["id"]:
            return jsonify({"error": "Forbidden"}), 403

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

    if not can_solve_ticket(repo, g.current_user["id"]):
        return jsonify({"error": "Only Moneda users can mark a ticket as solved"}), 403

    try:
        enforce_open_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    solved = repo.solve_ticket(ticket_id=ticket_id, actor_user_id=g.current_user["id"])
    return jsonify(solved), 200


@bp.post("/<ticket_id>/propose-solved")
@auth_required()
def propose_ticket_solved(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    role = repo.get_user_role(g.current_user["id"])
    if role not in VALID_ROLES:
        role = "outsider"

    if role not in {"solver", "moneda"}:
        return jsonify({"error": "Only Solver or Moneda users can propose solved"}), 403

    try:
        enforce_open_or_superuser(repo, ticket, g.current_user["id"])
    except AuthorizationError as exc:
        return jsonify({"error": str(exc)}), 403

    repo.create_event(
        ticket_id=ticket_id,
        actor_user_id=g.current_user["id"],
        event_type="solve_proposed",
        metadata={"status": ticket.get("status")},
    )
    return jsonify({"ok": True}), 200


@bp.get("/<ticket_id>/comments")
@auth_required()
def list_ticket_comments(ticket_id: str):
    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    if not can_access_ticket_list(repo, g.current_user["id"]):
        if ticket.get("owner_user_id") != g.current_user["id"]:
            return jsonify({"error": "Forbidden"}), 403

    comments = repo.list_ticket_comments(ticket_id)
    if not comments:
        return jsonify([]), 200

    comment_ids = [item["id"] for item in comments]
    author_ids = sorted({item.get("author_user_id") for item in comments if item.get("author_user_id")})
    users = repo.get_users_by_ids(author_ids)
    user_map = {u["id"]: u.get("external_username", "") for u in users}

    mentions = repo.list_comment_mentions(comment_ids)
    mention_map: dict[str, list[str]] = {}
    mention_user_ids = sorted({item["mentioned_user_id"] for item in mentions if item.get("mentioned_user_id")})
    mention_users = repo.get_users_by_ids(mention_user_ids)
    mention_user_map = {u["id"]: u.get("external_username", "") for u in mention_users}
    for mention in mentions:
        comment_id = mention.get("comment_id")
        mentioned_user_id = mention.get("mentioned_user_id")
        if not comment_id or not mentioned_user_id:
            continue
        mention_map.setdefault(comment_id, []).append(mention_user_map.get(mentioned_user_id, ""))

    for comment in comments:
        comment["author_username"] = user_map.get(comment.get("author_user_id"), "")
        comment["mentions"] = [item for item in mention_map.get(comment["id"], []) if item]

    return jsonify(comments), 200


@bp.post("/<ticket_id>/comments")
@auth_required()
def create_ticket_comment(ticket_id: str):
    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    parent_comment_id = payload.get("parent_comment_id")
    mark_type = (payload.get("mark_type") or "").strip().lower() or None

    if not body:
        return jsonify({"error": "Comment body is required"}), 400
    if mark_type and mark_type not in VALID_COMMENT_MARKS:
        return jsonify({"error": "mark_type must be one of: ticket, sandwatch"}), 400

    repo = current_app.extensions["repo"]
    ticket = repo.get_ticket(ticket_id)

    if not can_access_ticket_list(repo, g.current_user["id"]):
        if ticket.get("owner_user_id") != g.current_user["id"]:
            return jsonify({"error": "Forbidden"}), 403

    if parent_comment_id:
        parent = repo.get_ticket_comment(parent_comment_id)
        if parent.get("ticket_id") != ticket_id:
            return jsonify({"error": "Reply comment must belong to the same ticket"}), 400

    created = repo.create_ticket_comment(
        {
            "ticket_id": ticket_id,
            "author_user_id": g.current_user["id"],
            "parent_comment_id": parent_comment_id,
            "body": body,
            "mark_type": mark_type,
        }
    )

    mentioned_usernames = _extract_mentions(body)
    mentioned_users = repo.get_users_by_external_usernames(mentioned_usernames)
    mentioned_user_ids = [u["id"] for u in mentioned_users]
    repo.create_comment_mentions(created["id"], mentioned_user_ids)

    recipients = set()

    if ticket.get("solved_by_user_id"):
        recipients.add(ticket["solved_by_user_id"])

    if parent_comment_id:
        parent = repo.get_ticket_comment(parent_comment_id)
        if parent.get("author_user_id"):
            recipients.add(parent["author_user_id"])

    for user_id in mentioned_user_ids:
        recipients.add(user_id)

    recipients.discard(g.current_user["id"])

    notification_rows = [
        {
            "user_id": user_id,
            "ticket_id": ticket_id,
            "comment_id": created["id"],
            "kind": "comment",
            "payload": {
                "parent_comment_id": parent_comment_id,
                "mark_type": mark_type,
                "from_user_id": g.current_user["id"],
            },
            "is_read": False,
            "read_at": None,
            "created_at": _now_iso(),
        }
        for user_id in sorted(recipients)
    ]

    if notification_rows:
        repo.create_notifications(notification_rows)

    repo.create_event(
        ticket_id=ticket_id,
        actor_user_id=g.current_user["id"],
        event_type="commented",
        metadata={
            "comment_id": created["id"],
            "parent_comment_id": parent_comment_id,
            "mentions": [u.get("external_username") for u in mentioned_users],
            "mark_type": mark_type,
        },
    )

    created["mentions"] = [u.get("external_username") for u in mentioned_users]
    created["author_username"] = g.current_user.get("external_username", "")
    return jsonify(created), 201


@bp.patch("/<ticket_id>/comments/<comment_id>")
@auth_required()
def edit_ticket_comment(ticket_id: str, comment_id: str):
    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    mark_type = (payload.get("mark_type") or "").strip().lower() or None

    if not body:
        return jsonify({"error": "Comment body is required"}), 400
    if mark_type and mark_type not in VALID_COMMENT_MARKS:
        return jsonify({"error": "mark_type must be one of: ticket, sandwatch"}), 400

    repo = current_app.extensions["repo"]
    comment = repo.get_ticket_comment(comment_id)

    if comment.get("ticket_id") != ticket_id:
        return jsonify({"error": "Comment does not belong to this ticket"}), 400

    if comment.get("author_user_id") != g.current_user["id"]:
        return jsonify({"error": "Only the comment author can edit this comment"}), 403

    updated = repo.update_ticket_comment(
        comment_id=comment_id,
        updates={
            "body": body,
            "mark_type": mark_type,
            "updated_at": _now_iso(),
        },
    )

    mentioned_usernames = _extract_mentions(body)
    mentioned_users = repo.get_users_by_external_usernames(mentioned_usernames)
    mentioned_user_ids = [u["id"] for u in mentioned_users]
    repo.delete_comment_mentions(comment_id)
    repo.create_comment_mentions(comment_id, mentioned_user_ids)

    updated["mentions"] = [u.get("external_username") for u in mentioned_users]
    updated["author_username"] = g.current_user.get("external_username", "")
    return jsonify(updated), 200


@bp.delete("/<ticket_id>/comments/<comment_id>")
@auth_required()
def delete_ticket_comment(ticket_id: str, comment_id: str):
    repo = current_app.extensions["repo"]
    comment = repo.get_ticket_comment(comment_id)

    if comment.get("ticket_id") != ticket_id:
        return jsonify({"error": "Comment does not belong to this ticket"}), 400

    if comment.get("author_user_id") != g.current_user["id"]:
        return jsonify({"error": "Only the comment author can delete this comment"}), 403

    repo.delete_ticket_comment(comment_id)
    return jsonify({"ok": True}), 200


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
