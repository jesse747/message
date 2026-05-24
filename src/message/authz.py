from functools import wraps

from flask import abort, g, request
from flask_jwt_extended import get_jwt_identity

from .extensions import db
from .models import GroupMember, Person, Team, User


def _current_user():
    identity = get_jwt_identity()
    if identity is None:
        return None
    uid = getattr(identity, "id", identity)
    return db.session.get(User, uid)


def require_authenticated(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            abort(401)
        g.current_user = user
        return f(*args, **kwargs)

    return wrapper


def require_capability(*capabilities):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = _current_user()
            if not user:
                abort(401)
            if any(user.has_capability(c) for c in capabilities):
                g.current_user = user
                return f(*args, **kwargs)
            abort(403, "Insufficient permissions")

        return wrapper

    return decorator


def require_super_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            abort(401)
        if user.is_super_admin:
            g.current_user = user
            return f(*args, **kwargs)
        abort(403)

    return wrapper


def require_group_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            abort(401)
        if user.is_super_admin or user.has_capability("manage_groups"):
            g.current_user = user
            return f(*args, **kwargs)
        group_id = request.view_args.get("id") or request.view_args.get("group_id")
        if group_id:
            person = Person.query.filter_by(user_id=user.id).first()
            if person and GroupMember.query.filter_by(
                group_id=group_id, person_id=person.id, role="admin"
            ).first():
                g.current_user = user
                return f(*args, **kwargs)
        abort(403, "Group admin access required")

    return wrapper


def require_group_member(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            abort(401)
        if user.is_super_admin:
            g.current_user = user
            return f(*args, **kwargs)
        group_id = request.view_args.get("id") or request.view_args.get("group_id")
        if group_id:
            person = Person.query.filter_by(user_id=user.id).first()
            if person and GroupMember.query.filter_by(
                group_id=group_id, person_id=person.id
            ).first():
                g.current_user = user
                return f(*args, **kwargs)
        abort(403, "Group membership required")

    return wrapper


def require_team_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            abort(401)
        if user.is_super_admin or user.has_capability("manage_teams"):
            g.current_user = user
            return f(*args, **kwargs)
        team_id = request.view_args.get("id") or request.view_args.get("team_id")
        if team_id:
            person = Person.query.filter_by(user_id=user.id).first()
            if person:
                team = db.session.get(Team, team_id)
                if team and team.team_admin_id == person.id:
                    g.current_user = user
                    return f(*args, **kwargs)
        abort(403, "Team admin access required")

    return wrapper


def require_self(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = _current_user()
        if not user:
            abort(401)
        target_id = request.view_args.get("id")
        if target_id and int(target_id) == user.id:
            g.current_user = user
            return f(*args, **kwargs)
        if user.is_super_admin or user.has_capability("manage_users"):
            g.current_user = user
            return f(*args, **kwargs)
        abort(403)

    return wrapper
