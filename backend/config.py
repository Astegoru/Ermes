import os
from dataclasses import dataclass


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    secret_key: str
    jwt_secret: str
    jwt_access_minutes: int
    jwt_refresh_days: int
    facts_token_url: str
    supabase_url: str
    supabase_key: str
    supabase_storage_bucket: str
    max_upload_size_mb: int
    allowed_upload_mime_types: tuple[str, ...]
    allowed_upload_extensions: tuple[str, ...]
    admin_username: str
    admin_password: str
    debug: bool



def load_settings() -> Settings:
    allowed_mime = os.getenv(
        "ALLOWED_UPLOAD_MIME_TYPES",
        "image/jpeg,image/png,image/webp,application/pdf,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    allowed_ext = os.getenv("ALLOWED_UPLOAD_EXTENSIONS", ".jpg,.jpeg,.png,.webp,.pdf,.xls,.xlsx")

    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        secret_key=os.getenv("FLASK_SECRET_KEY", "change-me"),
        jwt_secret=os.getenv("JWT_SECRET", "change-jwt-secret"),
        jwt_access_minutes=int(os.getenv("JWT_ACCESS_MINUTES", "30")),
        jwt_refresh_days=int(os.getenv("JWT_REFRESH_DAYS", "7")),
        facts_token_url=os.getenv("FACTS_TOKEN_URL", "https://apimoneda.facts.cl/api/auth/token/"),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        supabase_storage_bucket=os.getenv("SUPABASE_STORAGE_BUCKET", "ticket-files"),
        max_upload_size_mb=int(os.getenv("MAX_UPLOAD_SIZE_MB", "10")),
        allowed_upload_mime_types=tuple(t.strip() for t in allowed_mime.split(",") if t.strip()),
        allowed_upload_extensions=tuple(t.strip().lower() for t in allowed_ext.split(",") if t.strip()),
        admin_username=os.getenv("ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("ADMIN_PASSWORD", "change-admin-password"),
        debug=_get_bool("DEBUG", default=False),
    )
