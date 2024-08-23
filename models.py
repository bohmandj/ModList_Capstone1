"""SWLAlchemy models for Capstone"""

from app import app

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
    
db = SQLAlchemy(app, model_class=Base)

###########################################################
# Association Tables:

follow_user = db.Table(
    """Connection of a user to the user profiles they follow."""
    
    'follow_user',

    db.Column(
        'user_id', 
        db.ForeignKey('User.id', ondelete='CASCADE'), 
        primary_key=True
    ),
        
    db.Column(
        'followed_profile_id', 
        db.ForeignKey('User.id', ondelete='CASCADE'), 
        primary_key=True
    ),
)


follow_modlist = db.Table(
    """Connection of a user to the modlists they follow."""
    
    'follow_modlist',

    db.Column(
        'user_id', 
        db.ForeignKey('User.id', ondelete='CASCADE'), 
        primary_key=True
    ),
        
    db.Column(
        'modlist_id', 
        db.ForeignKey('Modlist.id', ondelete='CASCADE'), 
        primary_key=True
    ),
)


conflicting_mod = db.Table(
    """Connection of a mod to the mods it conflicts 
    with and should not be installed together."""
    
    'conflicting_mod',

    db.Column( 
        'left_mod_id', 
        db.Integer,
        db.ForeignKey('Mod.id', ondelete='CASCADE'), 
        primary_key=True
    ),
        
    db.Column( 
        'right_mod_id', 
        db.Integer,
        db.ForeignKey('Mod.id', ondelete='CASCADE'), 
        primary_key=True
    ),
)


required_mod = db.Table(
    """Connection of a mod to the mods required 
    for it to function."""
    
    'required_mod',

    db.Column(
        'mod_id', 
        db.ForeignKey('Mod.id', ondelete='CASCADE'), 
        primary_key=True
    ),
        
    db.Column(
        'required_mod_id', 
        db.ForeignKey('Mod.id', ondelete='CASCADE'), 
        primary_key=True
    ),
)


keep_tracked = db.Table(
    """Connection of a user to the mods they want to put in the 'Keep Tracked' 
    section of their 'Tracked on Nexus' modlist."""
    
    'keep_tracked',

    db.Column(
        'user_id', 
        db.ForeignKey('User.id', ondelete='CASCADE'), 
        primary_key=True
    ),
        
    db.Column(
        'tracked_mod_id', 
        db.ForeignKey('Mod.id', ondelete='CASCADE'), 
        primary_key=True
    ),
)


modlist_mod = db.Table(
    """Connection of a modlist to the user who created/owns it."""
    
    'modlist_mod',
        
    db.Column(
        'modlist_id', 
        db.ForeignKey('Modlist.id', ondelete='CASCADE'), 
        primary_key=True
    ),

    db.Column(
        'mod_id', 
        db.ForeignKey('Mod.id', ondelete='CASCADE'), 
        primary_key=True
    ),
)


###########################################################
# Association Object:

class User_Mod_Notes(db.Model):
    """Connection of a modlist to the mods it contains.
    Also retains user's notes for this mod in this list.
    
    !!!! Do not attempt to read AND write in same transaction. 
    Changes on one will not show up in another until the 
    Session is expired, which normally occurs automatically 
    after Session.commit(). !!!!"""

    __tablename__ = 'user_mod_connection'

    modlist_id: Mapped[int] = mapped_column(
        db.ForeignKey('modlists.id'), 
        primary_key=True,
        autoincrement=False
    )
    mod_id: Mapped[int] = mapped_column(
        db.ForeignKey('mods.id'), 
        primary_key=True,
        autoincrement=False
    )

    notes: Mapped[str] = mapped_column(db.Text, default='')

    # association between User_Mod_Notes -> Mod
    mod: Mapped['Mod'] = db.relationship(back_populates='user_mod_notes')

    # association between User_Mod_Notes -> Modlist
    modlist: Mapped['Modlist'] = db.relationship(back_populates='user_mod_notes')


###########################################################
# Model Classes:

class Modlist(db.Model):
    """A list of game mods made by a user."""

    __tablename__ = 'modlists'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(60),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        nullable=False
    )
    user = db.relationship('User') # user that made/owns the modlist

    
    game_id = db.Column(
        db.Integer,
        db.ForeignKey('games.id', ondelete='CASCADE'),
        nullable=False
    )
    game = db.relationship('Game') # game the modlist is built for

    # list of mods added to the modlist
    mods = db.relationship(
        'Mod',
        secondary='mlist_mods'
    )

    # users that follow this modlist
    followers = db.relationship(
        'User',
        secondary='fol_mlists'
    )

    def __repr__(self):
        return f'<ModList #{self.id}: "{self.name}", by {self.user.username}>'

	############################ Need function to check modlist for NSFW, or bool attribute for entire list


class Mod(db.Model):
    """A package of files used to modify games 
    hosted on Nexus Mods website."""

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

    # modlists made/owned by the user
    modlists = db.relationship('Modlist')

    # modlists the user follows
    followed_modlists = db.relationship(
        'Modlist',
        secondary='fol_mlists'
    )

    #  mods user is actually using Nexus Tracking for
    keep_tracked = db.relationship(
        'Mod',
        secondary='keep_tracked'
    )

    # profiles this user follows
    followed_profiles = db.relationship(
        'User',
        secondary="fol_users",
        primaryjoin=(Follow_User.user_id == id),
        secondaryjoin=(Follow_User.followed_profile_id == id)
    )

    # profiles that follow this user
    followers = db.relationship(
        'User',
        secondary="fol_users",
        primaryjoin=(Follow_User.followed_profile_id == id),
        secondaryjoin=(Follow_User.user_id == id)
    )

    def is_followed_by_profile(self, profile):
        """Is this user followed by `profile`? Returns bool"""

        found_users = [user for user in self.followers if user == profile]
        return len(found_users) == 1

    def is_following_profile(self, profile):
        """Is this user following 'profile'? Returns bool"""

        found_users = [user for user in self.followed_profiles if user == profile]
        return len(found_users) == 1

    def is_following_modlist(self, modlist):
        """Is this user following 'modlist'? Returns bool"""

        found_modlists = [mlist for mlist in self.followed_modlists if mlist == modlist]
        return len(found_modlists) == 1

    def get_games(self):
        """Get list of games the user has made 
        lists for (probably owns the game)"""

        found_games = [mlist.game for mlist in self.modlists if mlist.game not in found_games]

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"





def connect_db(app):
    """Connect this database to provided Flask app.

    Call this in the Flask app.
    """

    db.app = app
    db.init_app(app)