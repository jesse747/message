import click
from flask.cli import with_appcontext

from .extensions import db
from .models import AppSetting, EventType, Family, Organization, OrganizationContact, Person, User


@click.command("seed")
@click.option("--superuser", is_flag=True, help="Create superuser only")
@with_appcontext
def seed_command(superuser):
    """Seed the database with initial data."""
    _seed_superuser()
    _seed_event_types()
    _seed_app_settings()
    if superuser:
        return
    _seed_organization()
    _seed_families()
    click.echo("Seed complete.")


def _seed_superuser():
    if User.query.filter_by(username="admin").first():
        click.echo("Superuser already exists, skipping.")
        return

    user = User(
        username="admin",
        email="admin@example.com",
        display_name="Admin",
        is_super_admin=True,
    )
    user.set_password("changeme")
    db.session.add(user)
    db.session.flush()

    person = Person(
        first_name="Admin",
        last_name="User",
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add(person)
    db.session.commit()
    click.echo("Created superuser: admin / changeme")


DEFAULT_EVENT_TYPES = [
    ("Baptism", "Water baptism ceremony", 0),
    ("Confirmation", "Confirmation of faith", 1),
    ("First Communion", "First participation in communion", 2),
    ("Wedding", "Marriage ceremony", 3),
    ("Funeral", "Funeral or memorial service", 4),
    ("Membership Started", "Became a church member", 5),
    ("Transfer", "Transferred from another church", 6),
    ("Child Dedication", "Child dedication ceremony", 7),
    ("Profession of Faith", "Public profession of faith", 8),
    ("Other", "Other significant life event", 99),
]


def _seed_event_types():
    existing = {et.name for et in EventType.query.all()}
    added = 0
    for name, description, sort_order in DEFAULT_EVENT_TYPES:
        if name not in existing:
            db.session.add(EventType(name=name, description=description, sort_order=sort_order))
            added += 1
    if added:
        db.session.commit()
        click.echo(f"Created {added} event types.")
    else:
        click.echo("Event types already exist, skipping.")


DEFAULT_APP_SETTINGS = [
    ("timezone", "America/Chicago", True),
    ("default_calendar_view", "month", True),
    ("default_page_size", "20", True),
]


def _seed_app_settings():
    existing = {s.key for s in AppSetting.query.all()}
    added = 0
    for key, value, is_public in DEFAULT_APP_SETTINGS:
        if key not in existing:
            db.session.add(AppSetting(key=key, value=value, is_public=is_public))
            added += 1
    if added:
        db.session.commit()
        click.echo(f"Created {added} app settings.")
    else:
        click.echo("App settings already exist, skipping.")


def _seed_organization():
    org = Organization.query.first()
    if org:
        click.echo("Organization already exists, skipping.")
        return

    org = Organization(
        name="My Church",
        description="",
        email="office@mychurch.org",
        phone="+1-555-123-4567",
        address="123 Main St, Anytown, ST 12345",
        website="https://mychurch.org",
    )
    db.session.add(org)
    db.session.flush()

    admin_person = Person.query.filter_by(first_name="Admin").first()
    if admin_person:
        contact = OrganizationContact(person_id=admin_person.id, role="Administrator")
        db.session.add(contact)

    db.session.commit()
    click.echo("Created organization: My Church")


def _seed_families():
    ungrouped = Person.query.filter(Person.family_id.is_(None)).all()
    if not ungrouped:
        return


    last_name_groups = {}
    for p in ungrouped:
        last_name_groups.setdefault(p.last_name, []).append(p)

    for last_name, persons in last_name_groups.items():
        family = Family(name=f"{last_name} Family")
        db.session.add(family)
        db.session.flush()
        for p in persons:
            p.family_id = family.id

    db.session.commit()
    count = len(ungrouped)
    click.echo(f"Created {len(last_name_groups)} families for {count} persons.")


@click.command("create-admin")
@click.option("--username", required=True, prompt=True)
@click.option("--email", required=True, prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--first-name", required=True, prompt=True)
@click.option("--last-name", default="", prompt=False)
@with_appcontext
def create_admin(username, email, password, first_name, last_name):
    """Create a super admin user and person record."""
    if User.query.filter_by(username=username).first():
        click.echo(f"Error: Username '{username}' already exists.")
        raise SystemExit(1)

    user = User(
        username=username,
        email=email,
        display_name=first_name,
        is_super_admin=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    person = Person(
        first_name=first_name,
        last_name=last_name,
        email_personal=email,
        user_id=user.id,
        created_by=user.id,
    )
    db.session.add(person)
    db.session.commit()

    click.echo(f"Created super admin: {username}")


def init_cli(app):
    app.cli.add_command(seed_command)
    app.cli.add_command(create_admin)
