"""SWLAlchemy models for Capstone"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Mod(db.Model):
    """A package of files used to modify games hosted on Nexus Mods website."""

    __tablename__ = 'mods'

    # mod id will match the id stored on Nexus
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(60),
        nullable=False
    )

    summary = db.Column(
        db.Text
    )
    
    game_id = db.Column(
        db.Integer,
        db.ForeignKey('games.id', ondelete='CASCADE'),
        nullable=False
    )
    game = db.relationship('Game') # game the modlist is built for

    required_mods = db.relationship(
        'Mod',
        secondary="req_mods",
        primaryjoin=(Required_Mod.mod_id == id),
        secondaryjoin=(Required_Mod.required_mod_id == id)
    )

    #################  NOT SURE BEST WAY TO CHECK KEY>VAL AND VAL>KEY  ###################### #askMentor
    conflicting_mods = db.relationship(
        'Mod',
        secondary="con_mods",
        primaryjoin=(Conflicting_Mod.mod_id == id),
        secondaryjoin=(Conflicting_Mod.conflicting_mod_id == id)
    )
    
    mods_with_conflicts = db.relationship(
        'Mod',
        secondary="con_mods",
        primaryjoin=(Conflicting_Mod.conflicting_mod_id == id),
        secondaryjoin=(Conflicting_Mod.mod_id == id)
    )

    def check_conflicts(self, checked_mlist):
        """Does this mod conflict with `other_mod`? 
        
        Returns list of mods: [{mod},{mod}] or None
        """

        con_mods = [mod for mod in self.conflicting_mods if mod in checked_mlist]
        con_mods.extend([mod for mod in self.mods_with_conflicts if mod in checked_mlist and mod not in con_mods])

        if len(con_mods) >= 1:
            return con_mods

        return None

    def check_requirements(self, checked_mlist):
        """Does this list have all the requirements stored for this mod?
        
        Returns list of required mods not in the list: [{mod},{mod}] or None
        """

        req_mods = [mod for mod in self.required_mods if mod not in checked_mlist]

        if len(req_mods) >= 1:
            return req_mods

        return None

    def __repr__(self):
        return f'<Nexus Mod #{self.id}: "{self.name}" for "{self.game_id}"\nDescription: {self.summary}>'




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

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"





def connect_db(app):
    """Connect this database to provided Flask app.

    Call this in the Flask app.
    """

    db.app = app
    db.init_app(app)