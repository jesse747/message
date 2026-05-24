import logging
import sys
import time

from sqlalchemy import event

logger = logging.getLogger("message")


class TextFormatter(logging.Formatter):
    def format(self, record):
        record.request_id = getattr(record, "request_id", "-")
        return super().format(record)

    def formatTime(self, record, datefmt=None):
        return super().formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json

        log = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "status", "ip", "method", "path", "duration_ms", "user_id"):
            val = getattr(record, key, None)
            if val is not None:
                log[key] = val

        return json.dumps(log, default=str)


def init_logging(app):
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    log_format = app.config.get("LOG_FORMAT", "text")

    root = logging.getLogger("message")
    root.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            TextFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root.handlers.clear()
    root.addHandler(handler)

    _install_slow_query_listener(app)


def _install_slow_query_listener(app):
    threshold = app.config["SLOW_QUERY_THRESHOLD_MS"]
    db_logger = logging.getLogger("message.db")

    @event.listens_for(__import__("sqlalchemy").engine.Engine, "before_cursor_execute")
    def before_query(conn, cursor, statement, parameters, context, executemany):
        conn._query_start = time.perf_counter()

    @event.listens_for(__import__("sqlalchemy").engine.Engine, "after_cursor_execute")
    def after_query(conn, cursor, statement, parameters, context, executemany):
        duration = (time.perf_counter() - conn._query_start) * 1000
        if duration > threshold:
            db_logger.warning(
                "slow query",
                extra={"duration_ms": round(duration, 1), "query": statement[:200]},
            )
