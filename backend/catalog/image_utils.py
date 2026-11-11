import logging
import mimetypes
import urllib.request
import uuid
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Max file size: 10MB
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 8


def download_external_image_to_storage(
    image_url: str,
    filename_prefix: str = "master_product",
) -> Optional[ContentFile]:
    """
    Downloads an image from an external HTTP/HTTPS URL and returns a Django ContentFile
    with a sanitized unique filename. When saved to a Model's FileField, Django automatically
    writes it to the configured default storage (AWS S3 in production or local media storage).

    Safeguards:
    - Verifies valid HTTP/HTTPS protocol.
    - Prevents re-downloading if already on platform's S3 domain or media URL.
    - Strict 8-second request timeout to avoid blocking bulk uploads.
    - 10MB maximum download cap to prevent memory exhaustion.
    - Infers safe image file extension (.jpg, .png, .webp).
    """
    if not image_url or not isinstance(image_url, str):
        return None

    clean_url = image_url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        return None

    # Check if URL is already hosted on our S3 bucket or local media server
    s3_domain = getattr(settings, "AWS_S3_CUSTOM_DOMAIN", "")
    if s3_domain and s3_domain in clean_url:
        return None
    media_url = getattr(settings, "MEDIA_URL", "/media/")
    if media_url and clean_url.startswith(media_url):
        return None

    try:
        req = urllib.request.Request(
            clean_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/118.0.0.0 Safari/537.36"
                ),
                "Accept": "image/*,*/*;q=0.8",
            },
        )
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            data = response.read(MAX_IMAGE_SIZE_BYTES + 1)
            if len(data) > MAX_IMAGE_SIZE_BYTES:
                logger.warning("Image from %s exceeded %s bytes limit; skipped.", clean_url, MAX_IMAGE_SIZE_BYTES)
                return None

            # Determine appropriate extension
            ext = ".jpg"
            if "webp" in content_type:
                ext = ".webp"
            elif "png" in content_type:
                ext = ".png"
            elif "gif" in content_type:
                ext = ".gif"
            elif "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            else:
                guessed = mimetypes.guess_extension(content_type)
                if guessed in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    ext = guessed

            filename = f"{filename_prefix}_{uuid.uuid4().hex[:12]}{ext}"
            return ContentFile(data, name=filename)
    except Exception as exc:
        logger.warning("Failed to auto-download image from %s: %s", clean_url, exc)
        return None
