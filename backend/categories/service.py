from backend.admin.service import is_superuser


def can_manage_category(repo, user_id: str) -> bool:
    return True
