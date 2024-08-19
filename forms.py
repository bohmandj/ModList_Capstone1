from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, validators


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', [
        validators.Length(min=4, max=25)
    ])
    email = StringField('Email Address', [
        validators.Length(min=6, max=35)
    ])
    password = PasswordField('New Password', [
        validators.InputRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')