from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class UpdatePasswordForm(FlaskForm):
    password = PasswordField(
        "New Password", validators=[DataRequired(), Length(min=6, max=30)]
    )
    confirm_password = PasswordField(
        "Confirm New Password",
        validators=[
            DataRequired(),
            Length(min=6, max=30),
            EqualTo("password", message="Passwords must match"),
        ],
    )
    submit = SubmitField("Update Password")
