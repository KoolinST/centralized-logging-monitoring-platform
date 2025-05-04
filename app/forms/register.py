from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField(
        "Email", validators=[DataRequired(), Email(), Length(min=5, max=74)]
    )
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

    def validate_email(self, email):
        from app.models.user import User

        user = User.query.filter(User.email.ilike(email.data)).first()
        if user:
            raise ValidationError(
                "This email is already taken. Please choose a different one."
            )

    def validate_username(self, username):
        from app.models.user import User

        user = User.query.filter(User.username.ilike(username.data)).first()
        if user:
            raise ValidationError(
                "This username is already taken. Please choose a different one."
            )
