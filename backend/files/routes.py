import os
import uuid
from flask import Blueprint, current_app, jsonify, request

from backend.auth.middleware import auth_required

bp = Blueprint("files", __name__, url_prefix="/api/files")


@bp.post("/upload")
@auth_required()
def upload_file():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    mime = file.mimetype or ""

    allowed_mimes: tuple = current_app.config["ALLOWED_UPLOAD_MIME_TYPES"]
    allowed_exts: tuple = current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    max_mb: int = current_app.config["MAX_UPLOAD_SIZE_MB"]

    if ext not in allowed_exts:
        return jsonify({"error": f"File extension '{ext}' is not allowed"}), 400

    if mime not in allowed_mimes:
        return jsonify({"error": f"File type '{mime}' is not allowed"}), 400

    file_bytes = file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_mb:
        return jsonify({"error": f"File exceeds the {max_mb} MB limit"}), 400

    storage_path = f"{uuid.uuid4()}{ext}"
    bucket: str = current_app.config["SUPABASE_STORAGE_BUCKET"]
    supabase = current_app.extensions["supabase"]

    try:
        supabase.storage.from_(bucket).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime},
        )
    except Exception as exc:
        current_app.logger.error("Storage upload failed: %s", exc)
        return jsonify({"error": "File upload failed"}), 500

    public_url = supabase.storage.from_(bucket).get_public_url(storage_path)

    return jsonify({"file_url": public_url, "file_type": mime}), 201
