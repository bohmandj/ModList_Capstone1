"""SWLAlchemy models for Capstone"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Game(db.Model):
    """A game for which Nexus hosts mods."""

    __tablename__ = 'games'

    # ID in this model will match Nexus game ID
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # slug of game name used by Nexus for game page url
    domain_name = db.Column(
        db.Text,
        nullable=False
    )

    name = db.Column(
        db.Text,
        nullable=False
    )

    def __repr__(self):
        return f'<Game #{self.id}: "{self.name}">'


class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True
    )

    password = db.Column(
        db.Text,
        nullable=False
    )

    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    is_moderator = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    hide_nsfw = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )





def connect_db(app):
    """Connect this database to provided Flask app.

    Call this in the Flask app.
    """

    db.app = app
    db.init_app(app)