from wtforms import PasswordField, SubmitField, StringField
from flask_wtf import FlaskForm
from wtforms.validators import DataRequired, Length, EqualTo


class SetUpPassword(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=6, max=14)]
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
