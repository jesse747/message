from datetime import datetime

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from ...extensions import db
from ...models import CalendarEvent, Meeting, Person

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
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
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

        elif event.frequency == "nth_weekday" and event.nth and event.weekday is not None and event.nth_month:
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
            CalendarEvent.frequency != "none",
            (
                CalendarEvent.last_date.is_(None)
                | (CalendarEvent.last_date >= from_date)
            ),
        ).all()

        for event in events:
            for d in _resolve_event_dates(event, from_date, to_date):
                items.append({
                    "type": "event",
                    "id": event.id,
                    "title": event.title,
                    "date": d.isoformat(),
                    "time": None,
                    "location": event.location,
                    "color": event.color,
                    "all_day": event.is_all_day,
                })

    # Meetings
    if "meetings" in wanted:
        meetings = Meeting.query.filter_by(is_active=True).all()
        current = from_date
        while current <= to_date:
            for m in meetings:
                if current.weekday() == m.day_of_week:
                    items.append({
                        "type": "meeting",
                        "id": m.id,
                        "title": m.name,
                        "date": current.isoformat(),
                        "time": str(m.time) if m.time else None,
                        "location": m.location,
                        "frequency": m.frequency,
                        "team_id": m.team_id,
                        "group_id": m.group_id,
                    })
            current += __import__("datetime").timedelta(days=1)

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
    return {"data": items}, 200
