import traceback

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from supabase import create_client

from backend.admin.routes import bp as admin_bp
from backend.auth.middleware import register_auth_guards
from backend.auth.routes import bp as auth_bp
from backend.categories.routes import bp as categories_bp
from backend.config import load_settings
from backend.db.repositories import Repositories
from backend.files_routes import bp as files_bp
from backend.tickets.routes import bp as tickets_bp


# Load local environment variables for development runs.
load_dotenv()



def create_app() -> Flask:
    settings = load_settings()
    app = Flask(__name__, template_folder="../frontend/templates")

    app.config.update(
        APP_ENV=settings.app_env,
        SECRET_KEY=settings.secret_key,
        JWT_SECRET=settings.jwt_secret,
        JWT_ACCESS_MINUTES=settings.jwt_access_minutes,
        JWT_REFRESH_DAYS=settings.jwt_refresh_days,
        FACTS_TOKEN_URL=settings.facts_token_url,
        SUPABASE_STORAGE_BUCKET=settings.supabase_storage_bucket,
        MAX_UPLOAD_SIZE_MB=settings.max_upload_size_mb,
        ALLOWED_UPLOAD_MIME_TYPES=settings.allowed_upload_mime_types,
        ALLOWED_UPLOAD_EXTENSIONS=settings.allowed_upload_extensions,
        ADMIN_USERNAME=settings.admin_username,
        ADMIN_PASSWORD=settings.admin_password,
    )

    app.extensions["supabase"] = None
    app.extensions["repo"] = None
    app.extensions["startup_error"] = None
    app.extensions["startup_traceback"] = None

    if not settings.supabase_url or not settings.supabase_key:
        app.extensions["startup_error"] = "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
    else:
        try:
            supabase_client = create_client(settings.supabase_url, settings.supabase_key)
            app.extensions["supabase"] = supabase_client
            app.extensions["repo"] = Repositories(supabase_client)
        except Exception as exc:
            app.extensions["startup_error"] = f"Supabase initialization failed: {exc}"
            app.extensions["startup_traceback"] = traceback.format_exc()

    @app.before_request
    def config_guard():
        startup_error = app.extensions.get("startup_error")
        startup_traceback = app.extensions.get("startup_traceback")
        if not startup_error:
            return None
        if request.path in {"/health", "/favicon.ico"}:
            return None
        payload = {
            "error": "Service configuration error",
            "detail": startup_error,
            "supabase_url": settings.supabase_url,
            "supabase_key": settings.supabase_key,
        }
        if startup_traceback:
            payload["traceback"] = startup_traceback
        return (
            jsonify(payload),
            503,
        )

    register_auth_guards(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(files_bp)

    @app.get("/health")
    def health():
        startup_error = app.extensions.get("startup_error")
        startup_traceback = app.extensions.get("startup_traceback")
        if app.config.get("APP_ENV") != "production":
            key_value = settings.supabase_key or ""
            key_prefix = key_value[:12] if key_value else ""
            diagnostics = {
                "app_env": settings.app_env,
                "supabase_url_set": bool(settings.supabase_url),
                "supabase_key_set": bool(key_value),
                "supabase_key_prefix": key_prefix,
                "supabase_key_length": len(key_value),
                "supabase_url": settings.supabase_url,
                "supabase_key": key_value,
            }
        else:
            diagnostics = None

        if startup_error:
            payload = {"status": "degraded", "error": startup_error}
            if startup_traceback:
                payload["traceback"] = startup_traceback
            if diagnostics is not None:
                payload["diagnostics"] = diagnostics
            return jsonify(payload), 503

        payload = {"status": "ok"}
        if diagnostics is not None:
            payload["diagnostics"] = diagnostics
        return jsonify(payload), 200

    @app.get("/favicon.ico")
    def favicon():
        # Return empty response to avoid noisy browser favicon fetch failures.
        return "", 204

    @app.get("/login")
    def login_view():
        return render_template("login.html")

    @app.get("/admin/login")
    def admin_login_view():
        return render_template("admin_login.html")

    @app.get("/")
    def index_view():
        return render_template("tickets_list.html")

    @app.get("/categories")
    def categories_view():
        return render_template("categories.html")

    @app.get("/tickets/new")
    def ticket_form_view():
        return render_template("ticket_form.html")

    @app.get("/tickets/trash")
    def ticket_trash_view():
        return render_template("ticket_trash.html")

    @app.get("/tickets/<ticket_id>")
    def ticket_detail_view(ticket_id: str):
        return render_template("ticket_detail.html", ticket_id=ticket_id)

    @app.get("/admin")
    def admin_panel_view():
        return render_template("admin_panel.html")

    @app.get("/admin/users")
    def admin_users_view():
        return render_template("admin_users.html")

    return app


app = create_app()
