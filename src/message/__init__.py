import os

from flask import Flask

from .config import config_by_name
from .errors import register_error_handlers
from .extensions import db, init_extensions
from .logging import init_logging
from .middleware import register_middleware

__all__ = ["create_app", "db"]

from . import models as _models_module  # noqa: F401 — register models with SQLAlchemy


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "dev")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["dev"]))

    init_extensions(app)
    init_logging(app)
    register_middleware(app)
    register_error_handlers(app)
    _register_blueprints(app)
    _register_cli(app)

    return app


def _register_cli(app):
    from .cli import init_cli

    init_cli(app)


def _register_blueprints(app):
    prefix = app.config["API_PREFIX"]

    from .blueprints.auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix=f"{prefix}/auth")

    from .blueprints.users import bp as users_bp

    app.register_blueprint(users_bp, url_prefix=f"{prefix}/users")

    from .blueprints.persons import bp as persons_bp

    app.register_blueprint(persons_bp, url_prefix=f"{prefix}/persons")

    from .blueprints.teams import bp as teams_bp

    app.register_blueprint(teams_bp, url_prefix=f"{prefix}/teams")

    from .blueprints.groups import bp as groups_bp

    app.register_blueprint(groups_bp, url_prefix=f"{prefix}/groups")

    from .blueprints.posts import bp as posts_bp

    app.register_blueprint(posts_bp, url_prefix=f"{prefix}/posts")

    from .blueprints.files import bp as files_bp

    app.register_blueprint(files_bp, url_prefix=f"{prefix}/files")

    from .blueprints.meetings import bp as meetings_bp

    app.register_blueprint(meetings_bp, url_prefix=f"{prefix}/meetings")

    from .blueprints.families import bp as families_bp

    app.register_blueprint(families_bp, url_prefix=f"{prefix}/families")

    from .blueprints.flocks import bp as flocks_bp

    app.register_blueprint(flocks_bp, url_prefix=f"{prefix}/flocks")

    from .blueprints.relationships import bp as relationships_bp

    app.register_blueprint(relationships_bp, url_prefix=f"{prefix}/relationships")

    from .blueprints.duty_groups import bp as duty_groups_bp

    app.register_blueprint(duty_groups_bp, url_prefix=f"{prefix}/duty-groups")

    from .blueprints.duties import bp as duties_bp

    app.register_blueprint(duties_bp, url_prefix=f"{prefix}/duties")

    from .blueprints.memberships import bp as memberships_bp

    app.register_blueprint(memberships_bp, url_prefix=f"{prefix}/memberships")

    from .blueprints.assignments import bp as assignments_bp

    app.register_blueprint(assignments_bp, url_prefix=f"{prefix}/assignments")

    from .blueprints.roster import bp as roster_bp

    app.register_blueprint(roster_bp, url_prefix=f"{prefix}/roster")

    from .blueprints.events import bp as events_bp

    app.register_blueprint(events_bp, url_prefix=f"{prefix}/events")

    from .blueprints.overrides import bp as overrides_bp

    app.register_blueprint(overrides_bp, url_prefix=f"{prefix}/overrides")

    from .blueprints.calendar import bp as calendar_bp

    app.register_blueprint(calendar_bp, url_prefix=f"{prefix}/calendar")

    from .blueprints.organization import bp as organization_bp

    app.register_blueprint(organization_bp, url_prefix=f"{prefix}/organization")

    from .blueprints.admin import bp as admin_bp

    app.register_blueprint(admin_bp, url_prefix=f"{prefix}/admin")

    from .blueprints.event_types import bp as event_types_bp

    app.register_blueprint(event_types_bp, url_prefix=f"{prefix}/event-types")

    from .blueprints.settings import bp as settings_bp

    app.register_blueprint(settings_bp, url_prefix=f"{prefix}/settings")
