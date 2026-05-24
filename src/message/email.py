from flask import current_app, render_template
from flask_mail import Message

from .extensions import mail
from .models import Organization


def _org_name():
    org = Organization.query.first()
    return org.name if org else current_app.config.get("APP_NAME", "Message")


def send_email(recipient, subject, template, context=None):
    if context is None:
        context = {}
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
    org_name = _org_name()

    ctx = {"org_name": org_name, "frontend_url": frontend_url, **context}

    html = render_template(f"email/{template}.html", **ctx)
    body = render_template(f"email/{template}.txt", **ctx)

    msg = Message(subject=subject, recipients=[recipient], html=html, body=body)
    mail.send(msg)


def send_invite_email(invite):
    try:
        send_email(
            invite.email,
            f"You're invited to join {_org_name()}",
            "invite",
            {
                "person_name": invite.person.full_name,
                "invite_code": invite.code,
                "register_url": (
                    f"{current_app.config.get('FRONTEND_URL', 'http://localhost:5173')}"
                    f"/register?code={invite.code}"
                ),
                "expires_at": invite.expires_at.strftime("%B %d, %Y"),
            },
        )
    except Exception:
        current_app.logger.exception("Failed to send invite email to %s", invite.email)


def send_password_reset_email(token):
    try:
        send_email(
            token.email,
            f"Password reset for {_org_name()}",
            "password_reset",
            {
                "reset_url": (
                    f"{current_app.config.get('FRONTEND_URL', 'http://localhost:5173')}"
                    f"/reset-password?token={token.code}"
                ),
                "expires_at": token.expires_at.strftime("%B %d, %Y at %H:%M"),
            },
        )
    except Exception:
        current_app.logger.exception(
            "Failed to send password reset email to %s", token.email
        )
