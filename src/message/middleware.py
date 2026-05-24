import time
import uuid

from flask import g, request

from .extensions import db
from .logging import logger


def register_middleware(app):
    @app.before_request
    def start_timer():
        g.request_id = uuid.uuid4().hex[:12]
        request._start_time = time.perf_counter()

    @app.after_request
    def log_request(response):
        if not app.config.get("ENABLE_REQUEST_LOGGING", True):
            return response

        duration = (time.perf_counter() - request._start_time) * 1000
        logger.info(
            "request",
            extra={
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration, 1),
                "ip": request.remote_addr,
                "user_id": g.get("jwt_identity"),
            },
        )
        return response
