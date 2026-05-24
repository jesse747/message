import hashlib
import time
import uuid
from datetime import UTC, datetime

from flask import g, request
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import db
from .logging import logger
from .models import IdempotencyRecord

_idempotency_cleanup_counter = 0


def register_middleware(app):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    @app.before_request
    def before():
        g.request_id = uuid.uuid4().hex[:12]
        request._start_time = time.perf_counter()

        if request.method not in ("POST", "PATCH", "PUT", "DELETE"):
            return

        idem_key = request.headers.get("Idempotency-Key", "").strip()
        if not idem_key:
            return

        body = request.get_data(as_text=True) or ""
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        g._idempotency_payload = (idem_key, body_hash)

        now = datetime.now(UTC)
        existing = IdempotencyRecord.query.filter_by(key=idem_key).first()
        if not existing:
            return

        expires = existing.expires_at
        if expires is not None:
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires < now:
                db.session.delete(existing)
                db.session.commit()
                return

        if existing.request_sha256 != body_hash:
            from .errors import error_response

            return error_response(
                "IDEMPOTENCY_KEY_REUSE",
                "Idempotency key already used with different payload",
                422,
            )

        return existing.response_body, existing.response_status, {
            "Content-Type": "application/json",
            "X-Idempotency-Replayed": "true",
        }

    @app.after_request
    def after(response):
        global _idempotency_cleanup_counter

        if app.config.get("ENABLE_REQUEST_LOGGING", True):
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

        payload = g.pop("_idempotency_payload", None)
        if payload is None:
            return response

        idem_key, body_hash = payload
        if not (
            isinstance(response.response, list)
            and response.response
            and response.status_code < 500
        ):
            return response

        existing = IdempotencyRecord.query.filter_by(key=idem_key).first()
        if existing:
            return response

        response_body = response.response[0].decode("utf-8") if isinstance(
            response.response[0], bytes
        ) else response.response[0]

        db.session.add(
            IdempotencyRecord(
                key=idem_key,
                request_method=request.method,
                request_path=request.path,
                request_sha256=body_hash,
                response_status=response.status_code,
                response_body=response_body,
            )
        )
        db.session.commit()

        _idempotency_cleanup_counter += 1
        if _idempotency_cleanup_counter % 50 == 0:
            now = datetime.now(UTC)
            IdempotencyRecord.query.filter(
                IdempotencyRecord.expires_at < now
            ).delete()
            db.session.commit()

        return response

    return app
