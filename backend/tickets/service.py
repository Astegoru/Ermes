from backend.admin.service import is_superuser


class AuthorizationError(Exception):
    pass


def enforce_owner_open_or_superuser(repo, ticket: dict, user_id: str) -> None:
    if is_superuser(repo, user_id):
        return

    if ticket.get("owner_user_id") != user_id:
        raise AuthorizationError("Only the owner can perform this action")

    if ticket.get("status") not in ("open", "in_progress"):
        raise AuthorizationError("Action allowed only when ticket is open or in progress")


def enforce_open_or_superuser(repo, ticket: dict, user_id: str) -> None:
    if is_superuser(repo, user_id):
        return

    if ticket.get("status") not in ("open", "in_progress"):
        raise AuthorizationError("Ticket must be open or in progress")


def enforce_owner_or_superuser(repo, ticket: dict, user_id: str) -> None:
    if is_superuser(repo, user_id):
        return

    if ticket.get("owner_user_id") != user_id:
        raise AuthorizationError("Only the owner can perform this action")
