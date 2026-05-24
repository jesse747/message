from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ...authz import require_capability
from ...extensions import db
from ...models import AppSetting, UserSetting

bp = Blueprint("settings", __name__)

VALIDATED_APP_KEYS = {
    "timezone": str,
    "default_calendar_view": frozenset({"month", "week", "agenda"}),
    "default_page_size": int,
}

VALIDATED_USER_KEYS = {
    "default_calendar_view": frozenset({"month", "week", "agenda"}),
    "default_page_size": int,
}


def _validate_key(known_keys, key, value):
    if key not in known_keys:
        return None
    validator = known_keys[key]
    if isinstance(validator, frozenset):
        if value not in validator:
            return None
        return value
    if validator is int:
        try:
            parsed = int(value)
            if parsed < 1 or parsed > 100:
                return None
            return str(parsed)
        except (ValueError, TypeError):
            return None
    if validator is str:
        return str(value)
    return None


def _settings_dict(settings):
    return {s.key: s.value for s in settings}


@bp.route("")
@jwt_required()
def get_app_settings():
    user_id = int(get_jwt_identity())
    from ...models import User

    user = db.session.get(User, user_id)
    is_admin = user and (user.is_super_admin or user.has_capability("manage_organization"))

    query = AppSetting.query
    if not is_admin:
        query = query.filter_by(is_public=True)
    settings = query.all()
    return {"data": _settings_dict(settings)}, 200


@bp.route("", methods=["PATCH"])
@jwt_required()
@require_capability("manage_organization")
def update_app_settings():
    data = request.get_json(silent=True) or {}
    user_id = int(get_jwt_identity())

    for key, raw_value in data.items():
        validated = _validate_key(VALIDATED_APP_KEYS, key, raw_value)
        if validated is None:
            return {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Invalid value for setting: {key}",
                }
            }, 422

        setting = AppSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = validated
            setting.updated_by = user_id
        else:
            db.session.add(
                AppSetting(key=key, value=validated, updated_by=user_id)
            )

    db.session.commit()
    settings = AppSetting.query.all()
    return {"data": _settings_dict(settings)}, 200


@bp.route("/user")
@jwt_required()
def get_user_settings():
    user_id = int(get_jwt_identity())
    settings = UserSetting.query.filter_by(user_id=user_id).all()
    return {"data": _settings_dict(settings)}, 200


@bp.route("/user", methods=["PATCH"])
@jwt_required()
def update_user_settings():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    for key, raw_value in data.items():
        if raw_value is None:
            setting = UserSetting.query.filter_by(user_id=user_id, key=key).first()
            if setting:
                db.session.delete(setting)
            continue

        validated = _validate_key(VALIDATED_USER_KEYS, key, raw_value)
        if validated is None:
            return {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Invalid value for setting: {key}",
                }
            }, 422

        setting = UserSetting.query.filter_by(user_id=user_id, key=key).first()
        if setting:
            setting.value = validated
        else:
            db.session.add(UserSetting(user_id=user_id, key=key, value=validated))

    db.session.commit()
    settings = UserSetting.query.filter_by(user_id=user_id).all()
    return {"data": _settings_dict(settings)}, 200
