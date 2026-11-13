"""Helpers for working with request payloads that may contain uploaded files."""

from django.http import QueryDict


def shallow_mutable_copy(data):
    """Return a mutable copy of request data WITHOUT deep-copying its values.

    ``QueryDict.copy()`` deep-copies every value. Uploaded files larger than
    FILE_UPLOAD_MAX_MEMORY_SIZE (2.5 MB) are open temporary files on disk, which cannot be
    deep-copied, so ``.copy()`` raised and the whole request returned 500. Sharing the same
    file objects is safe here because callers only add, replace or remove keys.
    """
    if isinstance(data, QueryDict):
        copy = QueryDict(mutable=True, encoding=data.encoding)
        for key, values in data.lists():
            copy.setlist(key, list(values))
        return copy
    return dict(data)
