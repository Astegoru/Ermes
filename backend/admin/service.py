from flask import current_app


ROLE_MONEDA = "moneda"
ROLE_SOLVER = "solver"
ROLE_OUTSIDER = "outsider"
VALID_ROLES = {ROLE_MONEDA, ROLE_SOLVER, ROLE_OUTSIDER}


def validate_admin_credentials(username: str, password: str) -> bool:
    return (
        username == current_app.config["ADMIN_USERNAME"]
        and password == current_app.config["ADMIN_PASSWORD"]
    )


def is_superuser(repo, user_id: str) -> bool:
    row = repo.get_superuser()
    if not row:
        return False
    return row.get("value") == user_id


def get_user_role(repo, user_id: str) -> str:
    if is_superuser(repo, user_id):
        return ROLE_MONEDA
    role = repo.get_user_role(user_id)
    if role not in VALID_ROLES:
        return ROLE_OUTSIDER
    return role


def can_access_ticket_list(repo, user_id: str) -> bool:
    return get_user_role(repo, user_id) in {ROLE_MONEDA, ROLE_SOLVER}


def can_manage_categories(repo, user_id: str) -> bool:
    return get_user_role(repo, user_id) == ROLE_MONEDA


def can_solve_ticket(repo, user_id: str) -> bool:
    return get_user_role(repo, user_id) == ROLE_MONEDA
