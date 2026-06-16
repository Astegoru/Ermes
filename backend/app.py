from flask import Flask, jsonify, render_template
from dotenv import load_dotenv
from supabase import create_client

from backend.admin.routes import bp as admin_bp
from backend.auth.middleware import register_auth_guards
from backend.auth.routes import bp as auth_bp
from backend.categories.routes import bp as categories_bp
from backend.config import load_settings
from backend.db.repositories import Repositories
from backend.files.routes import bp as files_bp
from backend.tickets.routes import bp as tickets_bp


# Load local environment variables for development runs.
load_dotenv()



def create_app() -> Flask:
    settings = load_settings()
    app = Flask(__name__, template_folder="../frontend/templates")

    app.config.update(
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

    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")

    supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    app.extensions["supabase"] = supabase_client
    app.extensions["repo"] = Repositories(supabase_client)

    register_auth_guards(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(files_bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

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
