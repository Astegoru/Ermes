from flask import current_app


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
