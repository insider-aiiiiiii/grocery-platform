from rest_framework.exceptions import APIException


class PasswordChangeRequired(APIException):
    status_code = 403
    default_detail = "Password change required."
    default_code = "PASSWORD_CHANGE_REQUIRED"


def authentication_exception_handler(exc, context):
    if isinstance(exc, PasswordChangeRequired):
        from rest_framework.response import Response

        return Response(
            {"detail": "Password change required.", "code": "PASSWORD_CHANGE_REQUIRED"},
            status=403,
        )
    from rest_framework.views import exception_handler

    return exception_handler(exc, context)
