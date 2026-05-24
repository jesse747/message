import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Family, Organization, OrganizationContact, Person, User


@click.command("seed")
@click.option("--superuser", is_flag=True, help="Create superuser only")
@with_appcontext
def seed_command(superuser):
    """Seed the database with initial data."""
    _seed_superuser()
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
