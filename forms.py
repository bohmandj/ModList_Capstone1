from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, validators


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


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', [
        validators.InputRequired()
    ])
    password = PasswordField('Password', [
        validators.Length(min=6)
    ])


class UserEditForm(FlaskForm):
    """Form for editing users."""

    username = StringField('Username', [
        validators.Length(min=4, max=25)
    ])
    email = StringField('Email Address', [
        validators.Length(min=6, max=35)
    ])
    hide_nsfw = BooleanField('Hide NSFW')
    new_password = PasswordField('New Password', [
        validators.Optional(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    new_confirm = PasswordField('Repeat New Password')
    current_password = PasswordField('New Password', [
        validators.InputRequired('Must provide current password to make changes')
    ])