from wtforms import PasswordField, SubmitField, StringField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from app.extensions import db
from sqlalchemy import select


class SetUpPassword(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=4, max=16)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=30)]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            Length(min=6, max=30),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Sign Up")

    def validate_username(self, username):
        from app.models.user import User

        user = db.session.scalar(select(User).where(User.username.ilike(username.data)))
        if user:
            raise ValidationError("Username already registered.")
