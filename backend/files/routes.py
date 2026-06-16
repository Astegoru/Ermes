import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from backend.auth.middleware import auth_required

bp = Blueprint("files", __name__, url_prefix="/api/files")


@bp.post("/upload")
@auth_required()
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "file field is required"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "filename is required"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    mime_type = file.content_type or "application/octet-stream"

    allowed_ext = current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]
    allowed_mime = current_app.config["ALLOWED_UPLOAD_MIME_TYPES"]

    if ext not in allowed_ext or mime_type not in allowed_mime:
        return jsonify({"error": "Invalid file type"}), 400

    content = file.read()
    max_bytes = current_app.config["MAX_UPLOAD_SIZE_MB"] * 1024 * 1024
    if len(content) > max_bytes:
        return jsonify({"error": "File exceeds max upload size"}), 400

    safe_name = secure_filename(file.filename)
    object_name = f"{uuid.uuid4().hex}_{safe_name}"

    client = current_app.extensions["supabase"]
    bucket = current_app.config["SUPABASE_STORAGE_BUCKET"]
    client.storage.from_(bucket).upload(object_name, content, {"content-type": mime_type})
    public_url = client.storage.from_(bucket).get_public_url(object_name)

    return (
        jsonify(
            {
                "file_url": public_url,
                "file_type": mime_type,
                "filename": safe_name,
                "size_bytes": len(content),
            }
        ),
        201,
    )
