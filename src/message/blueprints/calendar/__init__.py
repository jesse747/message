from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ...models import CalendarEvent, CalendarOverride, Meeting, MeetingInstance, Person

bp = Blueprint("calendar", __name__)

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _compute_easter(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    lunar = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lunar) // 451
    month = (h + lunar - 7 * m + 114) // 31
    day = (h + lunar - 7 * m + 114) % 31 + 1
    return datetime(year, month, day).date()


def _nth_weekday(year, month, n, weekday):
    from calendar import monthcalendar

    cal = monthcalendar(year, month)
    occurrences = [w[weekday] for w in cal if w[weekday] != 0]
    if n <= len(occurrences):
        return datetime(year, month, occurrences[n - 1]).date()
    return None


def _advent_sunday(year):
    christmas = datetime(year, 12, 25).date()
    sunday = christmas
    while sunday.weekday() != 6:
        sunday -= __import__("datetime").timedelta(days=1)
    for _ in range(3):
        sunday -= __import__("datetime").timedelta(days=7)
    return sunday


def _sunday_on_or_before(year, month, day):
    target = datetime(year, month, day).date()
    while target.weekday() != 6:
        target -= __import__("datetime").timedelta(days=1)
    return target


def _resolve_event_dates(event, from_date, to_date):
    if event.frequency == "none" and event.first_date:
        if from_date <= event.first_date <= to_date:
            return [event.first_date]
        return []

    start_year = from_date.year
    end_year = to_date.year
    dates = []

    for year in range(start_year, end_year + 1):
        if event.frequency == "fixed" and event.fixed_month and event.fixed_day:
            try:
                d = datetime(year, event.fixed_month, event.fixed_day).date()
                if from_date <= d <= to_date:
                    dates.append(d)
            except ValueError:
                pass

        elif event.frequency == "easter" and event.easter_offset is not None:
            d = _compute_easter(year)
            d += __import__("datetime").timedelta(days=event.easter_offset)
            if from_date <= d <= to_date:
                dates.append(d)

        elif event.frequency == "nth_weekday" and event.nth and event.weekday is not None \
                and event.nth_month:
            d = _nth_weekday(year, event.nth_month, event.nth, event.weekday)
            if d and from_date <= d <= to_date:
                dates.append(d)

        elif event.frequency == "advent_sunday":
            d = _advent_sunday(year)
            if from_date <= d <= to_date:
                dates.append(d)

        elif event.frequency == "sunday_on_or_before" and event.target_month and event.target_day:
            d = _sunday_on_or_before(year, event.target_month, event.target_day)
            if from_date <= d <= to_date:
                dates.append(d)

    return dates


@bp.route("")
@jwt_required()
def get_calendar():
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    sources = request.args.get("sources", "events,meetings,birthdays")

    if not date_from or not date_to:
        return {"error": {"code": "BAD_REQUEST", "message": "date_from and date_to required"}}, 400

    from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
    to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
    wanted = set(sources.split(","))

    items = []

    # Calendar events
    if "events" in wanted:
        events = CalendarEvent.query.filter(
            (
                (CalendarEvent.frequency != "none")
                & (
                    CalendarEvent.first_date.is_(None)
                    | (CalendarEvent.first_date <= to_date)
                )
                & (
                    CalendarEvent.last_date.is_(None)
                    | (CalendarEvent.last_date >= from_date)
                )
            )
            | (
                (CalendarEvent.frequency == "none")
                & (CalendarEvent.first_date >= from_date)
                & (CalendarEvent.first_date <= to_date)
            ),
        ).all()

        event_ids = [e.id for e in events]
        overrides_lookup = {}
        if event_ids:
            overrides = CalendarOverride.query.filter(
                CalendarOverride.event_id.in_(event_ids),
                CalendarOverride.date >= from_date,
                CalendarOverride.date <= to_date,
            ).all()
            for ov in overrides:
                overrides_lookup[(ov.event_id, ov.date)] = ov

        for event in events:
            for d in _resolve_event_dates(event, from_date, to_date):
                override = overrides_lookup.get((event.id, d))
                if override and override.is_cancelled:
                    continue
                items.append({
                    "type": "event",
                    "id": event.id,
                    "title": (
                        override.override_title
                        if (override and override.override_title)
                        else event.title
                    ),
                    "date": d.isoformat(),
                    "time": str(event.start_time) if event.start_time else None,
                    "end_time": str(event.end_time) if event.end_time else None,
                    "location": (
                        override.override_location
                        if (override and override.override_location)
                        else event.location
                    ),
                    "color": (
                        override.override_color
                        if (override and override.override_color)
                        else event.color
                    ),
                    "all_day": event.is_all_day,
                    "has_override": override is not None,
                })

    # Meetings
    if "meetings" in wanted:
        instances = (
            MeetingInstance.query
            .join(Meeting)
            .filter(
                Meeting.is_active.is_(True),
                MeetingInstance.date >= from_date,
                MeetingInstance.date <= to_date,
            )
            .order_by(MeetingInstance.date, MeetingInstance.time)
            .all()
        )
        for inst in instances:
            if inst.cancelled:
                continue
            items.append({
                "type": "meeting",
                "id": inst.meeting_id,
                "title": inst.meeting.name,
                "date": str(inst.date),
                "time": str(inst.time) if inst.time else None,
                "location": inst.location or inst.meeting.location,
                "frequency": inst.meeting.frequency,
                "team_id": inst.meeting.team_id,
                "group_id": inst.meeting.group_id,
                "cancellation_message": inst.cancellation_message,
            })

    # Birthdays
    if "birthdays" in wanted:
        people = Person.query.filter(Person.date_of_birth.isnot(None)).all()
        for p in people:
            for year in range(from_date.year, to_date.year + 1):
                try:
                    d = datetime(year, p.date_of_birth.month, p.date_of_birth.day).date()
                    if from_date <= d <= to_date:
                        items.append({
                            "type": "birthday",
                            "person_id": p.id,
                            "name": p.full_name,
                            "date": d.isoformat(),
                        })
                except ValueError:
                    pass

    items.sort(key=lambda x: (x["date"], x.get("time") or ""))
    limit = min(request.args.get("limit", 200, type=int), 500)
    has_more = len(items) > limit
    return {
        "data": items[:limit],
        "meta": {"has_more": has_more, "total": len(items)},
    }, 200
