import logging
import traceback

from flask import g, jsonify, request
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import ExpiredSignatureError
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger("message.errors")

CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


def error_response(code, message, status, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def log_error(status, message):
    logger.warning(
        "request_error",
        extra={
            "status": status,
            "message": message,
            "request_id": g.get("request_id"),
            "ip": request.remote_addr,
            "method": request.method,
            "path": request.path,
        },
    )


def generic_handler(error):
    status = getattr(error, "code", 500) if isinstance(error, HTTPException) else 500
    message = getattr(error, "description", str(error)) if isinstance(error, HTTPException) else "Internal server error"
    code = CODE_MAP.get(status, "INTERNAL_ERROR")

    log_error(status, message)

    if status == 500:
        traceback.print_exc()

    return error_response(code, message, status)


def marshmallow_handler(error):
    return error_response("VALIDATION_ERROR", "Validation failed", 422, details=error.messages)


def jwt_handler(error):
    mapping = {
        NoAuthorizationError: "Authorization header required",
        ExpiredSignatureError: "Token expired",
    }
    cls = type(error)
    message = mapping.get(cls, str(error))
    return error_response("UNAUTHORIZED", message, 401)


def register_error_handlers(app):
    for http_code in CODE_MAP:
        app.register_error_handler(http_code, generic_handler)

    app.register_error_handler(ValidationError, marshmallow_handler)
    app.register_error_handler(NoAuthorizationError, jwt_handler)
    app.register_error_handler(ExpiredSignatureError, jwt_handler)

    app.register_error_handler(Exception, generic_handler)
