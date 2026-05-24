import os
from datetime import timedelta

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'data.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "text")

    SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "500"))
    ENABLE_REQUEST_LOGGING = os.getenv("ENABLE_REQUEST_LOGGING", "true").lower() == "true"


class DevConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LOG_LEVEL = "CRITICAL"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)


class ProdConfig(Config):
    LOG_FORMAT = "json"

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Lax"


config_by_name = {
    "dev": DevConfig,
    "test": TestConfig,
    "prod": ProdConfig,
}
