"""Serve uploaded media with headers that stop a stored file from running as a web page."""

from django.views.static import serve

from config.uploads import ALLOWED_IMAGE_EXTENSIONS
from django.http import Http404


def serve_media(request, path, document_root=None):
    extension = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise Http404("Not an image.")
    response = serve(request, path, document_root=document_root)
    response["X-Content-Type-Options"] = "nosniff"
    # Even if a non-image slipped through, the browser must not execute it or let it frame.
    response["Content-Security-Policy"] = "sandbox; default-src 'none'; img-src 'self'; style-src 'none'"
    response["Cross-Origin-Resource-Policy"] = "cross-origin"
    return response
