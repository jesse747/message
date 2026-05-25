
from flasgger import Swagger
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()
swagger = Swagger()


def init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    frontend_url = app.config.get("FRONTEND_URL", "http://localhost:5173")
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": [frontend_url],
                "supports_credentials": True,
            }
        },
    )
    limiter.init_app(app)
    mail.init_app(app)

    swagger.init_app(app)

    app.config["SWAGGER"] = {
        "title": "Message API",
        "version": "1.0",
        "specs": [{"endpoint": "apispec", "route": "/apispec.json"}],
        "specs_route": "/docs",
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT token: Bearer <token>",
            }
        },
    }

    _register_jwt_callbacks()


def _register_jwt_callbacks():
    @jwt.invalid_token_loader
    def invalid_token_callback(_error):
        return {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}, 401

    @jwt.expired_token_loader
    def expired_token_callback(_jwt_header, _jwt_payload):
        return {"error": {"code": "UNAUTHORIZED", "message": "Token expired"}}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(_error):
        return {"error": {"code": "UNAUTHORIZED", "message": "Authorization header required"}}, 401
