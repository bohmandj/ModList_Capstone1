from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, BooleanField, validators


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username',
        [ validators.Regexp(
            '^[a-zA-Z0-9_.-]+$', 
            message="Username must contain only letters, numbers, dashes, periods, underscores"
        ),
        validators.Length(min=4, max=30) ], 
        description="Enter a username"
    )
    email = StringField('Email Address',
        [ validators.Length(min=6, max=30, 
            message="Email must contain at least 6, and no more than 30 characters") ], 
        description="Enter your email address"
    )
    password = PasswordField('New Password',
        [ validators.InputRequired() ], 
        description="Enter a password"
    )
    confirm = PasswordField('Confirm Password',
        [ validators.EqualTo('confirm', 
            message='"New Password" and "Confirm Password" must match') ]
        description="Re-enter your password"
    )


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username',
        [ validators.InputRequired() ], 
        description="Enter your username"
    )
    password = PasswordField('Password',
        [ validators.Length(min=6, 
            message="Password must contain at least 6 characters") ], 
        description="Enter your password"
    )


class UserEditForm(FlaskForm):
    """Form for editing users."""

    username = StringField('Username',
        [ validators.Regexp(
            '^[a-zA-Z0-9_.-]+$', 
            message="Username must contain only letters, numbers, dashes, periods, underscores"
        ),
        validators.Length(min=4, max=30) ], 
        description="Enter your new username"
    )
    email = StringField('Email Address', 
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
    current_password = PasswordField('Password',
        [ validators.Length(min=6, 
            message="Password must contain at least 6 characters") ], 
        description="Enter your password"
    )


class UserPasswordForm(FlaskForm):
    """Form to reset user password to a new password."""

    new_password = PasswordField('New Password',  
        description="Enter your new password"
    )
    new_confirm = PasswordField('Confirm New Password',
        [ validators.EqualTo('new_confirm', 
            message='"New Password" and "Confirm New Password" must match') ],
        description="Re-enter your new password"
    )
    current_password = PasswordField('Current Password',
        [ validators.Length(min=6, 
            message="Password must contain at least 6 characters") ], 
        description="Enter your current password"
    )


class ModlistAddForm(FlaskForm):
    """Form for adding ModLists"""

    name = StringField('Name', 
        [ validators.Length(min=1, max=60) ], 
        description="Enter a name for your ModList"
    )
    description = TextAreaField('Description', 
        [ validators.optional() ], 
        description="Tell us about your new ModList"
    )
    private = BooleanField(
        "Mark as Private",
        description="(Don't show this ModList on public profile page)",
        default='',
        false_values=(False, 'false', '')
    )


class ModlistEditForm(FlaskForm):
    """Form for editing modlists."""

    name = StringField('Name', 
        [ validators.Length(min=1, max=60) ], 
        description="Re-name for this ModList"
    )
    description = TextAreaField('Description', 
        [ validators.optional() ], 
        description="Describe this ModList"
    )
    private = BooleanField(
        "Mark as Private",
        description="(Don't show this ModList on public profile page)",
        default='',
        false_values=(False, 'false', '')
    )