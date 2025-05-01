from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Email


class LoginForm(FlaskForm):
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(min=5, max=74)]
    )
    password = PasswordField(
        "Password", validators=[DataRequired(), Length(min=6, max=30)]
    )
    submit = SubmitField("Login")
