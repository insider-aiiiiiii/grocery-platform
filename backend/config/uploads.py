"""Upload hardening: only real raster images, with a size cap."""

from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


def _detect_image_type(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    return None


def validate_image_upload(value) -> None:
    """Reject anything that is not a JPEG, PNG, GIF or WebP picture (no SVG, HTML or scripts).

    Only newly uploaded files are inspected; files already stored are left alone so old
    records can still be saved.
    """
    # A FieldFile already saved to storage is an old record: leave it alone. A fresh upload
    # arrives either as an UploadedFile (serializer) or an uncommitted FieldFile (model clean).
    if isinstance(value, FieldFile) and getattr(value, "_committed", False):
        return
    name = (getattr(value, "name", "") or "").lower()
    extension = name.rsplit(".", 1)[-1] if "." in name else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Upload a JPG, PNG, WebP or GIF image.", code="invalid_image_type")
    if getattr(value, "size", 0) > MAX_IMAGE_BYTES:
        raise ValidationError("Image must be 10 MB or smaller.", code="image_too_large")
    handle = value.file
    position = handle.tell() if hasattr(handle, "tell") else 0
    handle.seek(0)
    header = handle.read(12)
    handle.seek(position)
    detected = _detect_image_type(header)
    if detected is None or (detected == "jpeg") != (extension in {"jpg", "jpeg"}) and detected != extension:
        raise ValidationError("File content is not a valid image.", code="invalid_image_content")
