import os
from flask_mail import Message
from flask import url_for, flash, current_app
from app.extensions import mail, db


def send_confirmation_email(user):
    try:
        token = user.get_email_confirmation_token()
        db.session.commit()
        msg = Message(
            "Confirm Your Email",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user.email],
        )
        msg.body = (
            f"Hi {user.name},\n\n"
            f"To confirm your email address, please click the following link:\n\n"
            f"{url_for('auth.confirm_email', token=token, _external=True)}\n\n"
            f"After confirming your email, your account will be "
            f"reviewed by an administrator.\n\n"
            f"If you did not make this request, please ignore this email."
        )
        mail.send(msg)
        current_app.logger.info(f"Confirmation email sent to {user.email}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error sending confirmation email to {user.email}: {e}"
        )
        flash(
            "An error occurred while sending the confirmation email. Please try again.",
            "danger",
        )


def send_reset_password(user):
    try:
        token = user.get_reset_token()
        db.session.commit()
        msg = Message(
            "Password Reset Request",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user.email],
        )
        msg.body = (
            f"Hi {user.name},\n\n"
            f"To reset your password, please click the following link:\n\n"
            f"{url_for('password.reset_password', token=token, _external=True)}\n\n"
            f"This link will expire in 30 minutes.\n\n"
            f"If you did not make this request, please ignore this email."
        )
        mail.send(msg)
        current_app.logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error sending reset password email to {user.email}: {e}"
        )
        flash(
            "An error occurred while sending the password reset email. "
            "Please try again.",
            "danger",
        )


def send_admin_new_user_notification(user):
    """Notify all admins that a new user has registered and is pending approval."""
    try:
        from app.models.user import User
        from sqlalchemy import select

        admins = db.session.scalars(select(User).where(User.role == "admin")).all()
        if not admins:
            current_app.logger.warning(
                "No admins found to notify about new registration."
            )
            return
        admin_emails = [a.email for a in admins]
        msg = Message(
            "New User Registration. Action Required",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=admin_emails,
        )
        msg.body = (
            f"A new user has registered and is awaiting approval.\n\n"
            f"Name:     {user.name}\n"
            f"Username: {user.username}\n"
            f"Email:    {user.email}\n\n"
            f"Please review and approve or reject this account:\n"
            f"{url_for('admin.dashboard', _external=True)}\n"
        )
        mail.send(msg)
        current_app.logger.info(f"Admin notification sent for new user: {user.email}")
    except Exception as e:
        current_app.logger.error(
            f"Error sending admin notification for {user.email}: {e}"
        )


def send_approval_email(user):
    """Notify the user that their account has been approved."""
    try:
        msg = Message(
            "Your Account Has Been Approved",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user.email],
        )
        msg.body = (
            f"Hi {user.name},\n\n"
            f"Great news! Your account has been approved by an administrator.\n\n"
            f"You can now log in and access the platform:\n"
            f"{url_for('auth.login', _external=True)}\n\n"
            f"Your role: {user.role.capitalize()}\n\n"
            f"Welcome aboard!"
        )
        mail.send(msg)
        current_app.logger.info(f"Approval email sent to {user.email}")
    except Exception as e:
        current_app.logger.error(f"Error sending approval email to {user.email}: {e}")


def send_rejection_email(user):
    """Notify the user that their account has been rejected."""
    try:
        msg = Message(
            "Your Account Registration Was Not Approved",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user.email],
        )
        msg.body = (
            f"Hi {user.name},\n\n"
            f"Unfortunately, your account registration has not been approved "
            f"at this time.\n\n"
            f"If you believe this is a mistake, please contact the administrator.\n\n"
            f"Thank you."
        )
        mail.send(msg)
        current_app.logger.info(f"Rejection email sent to {user.email}")
    except Exception as e:
        current_app.logger.error(f"Error sending rejection email to {user.email}: {e}")
