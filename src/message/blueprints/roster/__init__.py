from datetime import datetime, timedelta

from flask import Blueprint, abort, request
from flask_jwt_extended import jwt_required

from ...extensions import db
from ...models import Duty, DutyAssignment, DutyGroup, DutyGroupMembership

bp = Blueprint("roster", __name__)


@bp.route("")
@jwt_required()
def get_roster():
    group_id = request.args.get("group_id", type=int)
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if not group_id or not date_from or not date_to:
        return {
            "error": {
                "code": "BAD_REQUEST",
                "message": "group_id, date_from, and date_to required",
            }
        }, 400

    group = db.session.get(DutyGroup, group_id) or abort(404)
    from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
    to_date = datetime.strptime(date_to, "%Y-%m-%d").date()

    duties = (
        Duty.query.filter_by(duty_group_id=group_id, is_active=True)
        .order_by(Duty.sort_order)
        .all()
    )
    memberships = DutyGroupMembership.query.filter_by(duty_group_id=group_id).filter(
        DutyGroupMembership.date_from <= to_date,
        (DutyGroupMembership.date_to.is_(None)) | (DutyGroupMembership.date_to >= from_date),
    ).all()

    current_date = from_date
    weeks = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    while current_date <= to_date:
        if current_date.weekday() == group.day_of_week:
            week_data = {"date": current_date.isoformat(), "duties": []}
            for d in duties:
                assignments = DutyAssignment.query.filter_by(duty_id=d.id, date=current_date).all()
                week_data["duties"].append({
                    "id": d.id,
                    "name": d.name,
                    "assignees": [
                        {"person_id": a.person_id, "name": a.person.full_name if a.person else None}
                        for a in assignments
                    ],
                })
            weeks.append(week_data)
        current_date += timedelta(days=1)

    return {
        "data": {
            "group": {
                "id": group.id,
                "name": group.name,
                "day": day_names[group.day_of_week] if group.day_of_week < 7 else "Unknown",
                "time": str(group.time) if group.time else None,
            },
            "available_pool": [
                {
                    "person_id": m.person_id,
                    "name": m.person.full_name if m.person else None,
                    "date_from": str(m.date_from),
                    "date_to": str(m.date_to) if m.date_to else None,
                }
                for m in memberships
            ],
            "weeks": weeks,
        }
    }, 200
