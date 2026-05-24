import hashlib

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)

    _register_jwt_callbacks()


def _register_jwt_callbacks():
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}, 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"error": {"code": "UNAUTHORIZED", "message": "Token expired"}}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"error": {"code": "UNAUTHORIZED", "message": "Authorization header required"}}, 401
