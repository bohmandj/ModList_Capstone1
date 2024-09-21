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
    hide_nsfw = BooleanField('Hide NSFW mod content?')
    current_password = PasswordField('New Password', [
        validators.Length(min=6)
    ])


class ModlistAddForm(FlaskForm):
    """Form for adding ModLists"""

    name = StringField('Name', [
        validators.Length(min=1, max=60)
    ])
    private = BooleanField(
        'Mark as Private - hide ModList from public profile', 
        false_values=('False', 'false', '')
    )
    description = TextAreaField('Description', [
        validators.optional()
    ])