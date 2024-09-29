from flask_wtf import FlaskForm
from wtforms import validators, widgets
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, SelectMultipleField


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField(
        'Username',
        [ validators.Regexp(
            '^[a-zA-Z0-9_.-]+$', 
            message="Username must contain only letters, numbers, dashes, periods, underscores"
        ),
        validators.Length(min=4, max=30) ], 
        description="Enter a username"
    )
    email = StringField(
        'Email Address',
        [ validators.Length(min=6, max=30, 
            message="Email must contain at least 6, and no more than 30 characters") ], 
        description="Enter your email address"
    )
    password = PasswordField(
        'New Password',
        [ validators.InputRequired() ], 
        description="Enter a password"
    )
    confirm = PasswordField(
        'Confirm Password',
        [ validators.EqualTo('password', 
            message='"New Password" and "Confirm Password" must match') ],
        description="Re-enter your password"
    )


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField(
        'Username',
        [ validators.InputRequired() ], 
        description="Enter your username"
    )
    password = PasswordField(
        'Password',
        [ validators.Length(min=6, 
            message="Password must contain at least 6 characters") ], 
        description="Enter your password"
    )


class UserEditForm(FlaskForm):
    """Form for editing users."""

    username = StringField(
        'Username',
        [ validators.Regexp(
            '^[a-zA-Z0-9_.-]+$', 
            message="Username must contain only letters, numbers, dashes, periods, underscores"
        ),
        validators.Length(min=4, max=30) ], 
        description="Enter your new username"
    )
    email = StringField(
        'Email Address', 
        [ validators.Length(min=6, max=30, 
            message="Email must contain at least 6, and no more than 30 characters") ], 
        description="Enter your new email address"
    )
    hide_nsfw = BooleanField(
        'Hide NSFW mod images?', 
        description="(Blurs title image of mods Nexus has marked as containing adult content.)",
        default='',
        false_values=(False, 'false', '')
    )
    current_password = PasswordField(
        'Password',
        [ validators.Length(min=6, 
            message="Password must contain at least 6 characters") ], 
        description="Enter your password"
    )


class UserPasswordForm(FlaskForm):
    """Form to reset user password to a new password."""

    new_password = PasswordField(
        'New Password',  
        description="Enter your new password"
    )
    new_confirm = PasswordField(
        'Confirm New Password',
        [ validators.EqualTo('new_password', 
            message='"New Password" and "Confirm New Password" must match') ],
        description="Re-enter your new password"
    )
    current_password = PasswordField(
        'Current Password',
        [ validators.Length(min=6, 
            message="Password must contain at least 6 characters") ], 
        description="Enter your current password"
    )


class ModlistAddForm(FlaskForm):
    """Form for adding ModLists"""

    name = StringField(
        'Name', 
        [ validators.Length(min=1, max=60) ], 
        description="Enter a name for your ModList"
    )
    description = TextAreaField(
        'Description', 
        [ validators.optional() ], 
        description="Tell us about your new ModList"
    )
    private = BooleanField(
        'Mark as Private',
        description="(Don't show this ModList on public profile page)",
        default='',
        false_values=(False, 'false', '')
    )


class ModlistEditForm(FlaskForm):
    """Form for editing modlists."""

    name = StringField(
        'Name', 
        [ validators.Length(min=1, max=60) ], 
        description="Re-name this ModList"
    )
    description = TextAreaField(
        'Description', 
        [ validators.optional() ], 
        description="Describe this ModList"
    )
    private = BooleanField(
        'Mark as Private',
        description="(Don't show this ModList on public profile page)",
        default='',
        false_values=(False, 'false', '')
    )


class MultiCheckboxField(SelectMultipleField):
    """Custom multi-checkbox field for picking 
    multiple ModLists to add a mod to."""
    widget = widgets.ListWidget(html_tag='ul', prefix_label=False)
    option_widget = widgets.CheckboxInput()

class MultiCheckboxAtLeastOne():
    """Custom validator requiring at least one ModList 
    to be selected in order to submit."""
    def __init__(self, message=None):
        if not message:
            message = 'At least one option must be selected.'
        self.message = message

    def __call__(self, form, field):
        if len(field.data) == 0:
            raise validators.StopValidation(self.message)

class ModlistAddModForm(FlaskForm):
    """Form for adding a Mod to a ModList"""

    users_modlists = MultiCheckboxField(
        'Pick one or more ModLists',
        validators=[MultiCheckboxAtLeastOne()], 
        validate_choice=False,
        coerce=int,
        description="Each selected Modlist will have this mod added to it"
    )