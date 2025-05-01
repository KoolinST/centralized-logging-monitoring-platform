import os
from flask_mail import Message
from flask import url_for, flash
from app import mail
import logging
import time
from app.extensions import db


# Initialize logger
logging_level = os.getenv("LOGGING_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, logging_level, logging.INFO))


def send_confirmation_email(user):
    try:
        token = user.get_email_confirmation_token()
        msg = Message(
            "Confirm Your Email",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user.email],
        )
        msg.body = f"""To confirm your email address, please click the following link:
                       {url_for('auth.confirm_email', token=token, _external=True)}
                       If you did not make this request, please ignore this email.
                   """
        mail.send(msg)
        user.email_confirmation_expiry = int(time.time())
        db.session.commit()
        logging.info(f"Confirmation email sent to {user.email}")

    except Exception as e:
        logging.error(f"Error occurred while sending confirmation email: {e}")
        flash(
            "An error occurred while sending the confirmation email. Please try again.",
            "danger",
        )


def send_reset_password(user):
    try:
        token = user.get_reset_token()
        msg = Message(
            "Password Reset Request",
            sender=os.getenv("MAIL_DEFAULT_SENDER"),
            recipients=[user.email],
        )
        msg.body = f"""To reset your password, please click the following link:
    {url_for('password.reset_password', token=token, _external=True)}
    If you did not make this request, please ignore this email.
    """
        mail.send(msg)
        user.password_reset_expiry = int(time.time())
        db.session.commit()
        logging.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        logging.error(f"Error occurred while sending reset password email: {e}")
        flash("An error occurred while sending the confirmation email.", "danger")
