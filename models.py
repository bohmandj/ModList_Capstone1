"""SWLAlchemy models for Capstone"""

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import List, Optional

class Base(DeclarativeBase):
    pass

bcrypt = Bcrypt()
db = SQLAlchemy(model_class=Base)

###########################################################
# Association Tables:

#Connection of a user to the user profiles they follow.
follow_user = db.Table(
    
    'follow_user',

    db.Column(
        'user_id', 
        db.ForeignKey('users.id'), 
        primary_key=True
    ),
        
    db.Column(
        'followed_profile_id', 
        db.ForeignKey('users.id'), 
        primary_key=True
    ),
)


#Connection of a user to the modlists they follow.
follow_modlist = db.Table(
    
    'follow_modlist',

    db.Column(
        'user_id', 
        db.ForeignKey('users.id'), 
        primary_key=True
    ),
        
    db.Column(
        'modlist_id', 
        db.ForeignKey('modlists.id'), 
        primary_key=True
    ),
)


#Connection of a mod to the mods it conflicts 
#with and should not be installed together.
mod_conflicts = db.Table(
    
    'mod_conflicts',

    db.Column( 
        'conflicting_mod_id', 
        db.Integer,
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
        
    db.Column( 
        'conflicted_mod_id', 
        db.Integer,
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
)


#Connection of a mod to the mods required 
#for it to function.
mod_requirements = db.Table(
    
    'mod_requirements',

    db.Column(
        'mod_id', 
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
        
    db.Column(
        'required_mod_id', 
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
)


#Connection of a user to the mods they want to put in the 'Keep Tracked' 
#section of their 'Tracked on Nexus' modlist.
keep_tracked = db.Table(
    
    'keep_tracked',

    db.Column(
        'user_id', 
        db.ForeignKey('users.id'), 
        primary_key=True
    ),
        
    db.Column(
        'tracked_mod_id', 
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
)


#Connection of a modlist to the mods in it.
modlist_mod = db.Table(
    
    'modlist_mod',
        
    db.Column(
        'modlist_id', 
        db.ForeignKey('modlists.id'), 
        primary_key=True
    ),

    db.Column(
        'mod_id', 
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
)


#Connection of a game to the mod that is made for it.
game_mod = db.Table(
    
    'game_mod',
        
    db.Column(
        'game_id', 
        db.ForeignKey('games.id'), 
        primary_key=True
    ),

    db.Column(
        'mod_id', 
        db.ForeignKey('mods.id'), 
        primary_key=True
    ),
)

###########################################################
# Association Object:

# Connection of a modlist to the mods it contains.
# Also retains user's notes for this mod in this list.

# !!!! Do not attempt to read AND write in same transaction. 
# Changes on one will not show up in another until the 
# Session is expired, which normally occurs automatically 
# after Session.commit(). !!!!
class User_Mod_Notes(db.Model):

    __tablename__ = 'user_mod_connection'

    user_id: Mapped[int] = mapped_column(
        db.ForeignKey('users.id'), 
        primary_key=True
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
    user: Mapped['User'] = db.relationship(back_populates='user_mod_notes')


###########################################################
# Model Classes:

# A list of game mods made by a user.
class Modlist(db.Model):

    __tablename__ = 'modlists'

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(db.String(60))

    description: Mapped[Optional[str]]

    has_nsfw: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=False
    )

    mods: Mapped[List['Mod']] = db.relationship(
        secondary=modlist_mod, 
        back_populates='in_modlists'
    )

    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id', ondelete='CASCADE'))
    user: Mapped['User'] = db.relationship(back_populates='modlists') # user that made/owns the modlist

    game_id: Mapped[int] = mapped_column(db.ForeignKey('games.id', ondelete='SET NULL'))
    for_game: Mapped['Game'] = db.relationship(back_populates='subject_of_modlists') # game the modlist is built for

    # users that follow this modlist
    followers: Mapped[List['User']] = db.relationship(
        secondary=follow_modlist, 
        back_populates='followed_modlists'
    )

    def __repr__(self):
        return f'<ModList #{self.id}: "{self.name}", by {self.user.username}>'


# A package of files used to modify games 
# hosted on Nexus Mods website.
class Mod(db.Model):

    __tablename__ = 'mods'

    # mod id must match the id stored on Nexus
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False
    )

    name: Mapped[str] = mapped_column(db.String(60))

    summary: Mapped[str] = mapped_column(
        db.Text, 
        default=''
    )

    in_modlists: Mapped[List['Modlist']] = db.relationship(
        secondary=modlist_mod, 
        back_populates='mods'
    )
    
    for_games: Mapped[List['Game']] = db.relationship(
        secondary=game_mod,
        back_populates='subject_of_mods'
    )

    # List of Users who have taken notes on this mod, 
    #   bypassing the `User_Mod_Notes` class
    users_with_notes: Mapped[List['User']] = db.relationship(
        secondary='user_mod_connection', 
        back_populates='mods_with_notes',
        viewonly=True
    )

    # List of 'User_Mod_Notes' objects for 
    #   User -> User_Mod_Notes -> Mod associated with this mod 
    # Each 'User_Mod_Notes' contains 'notes' by 'user' about 'mod'
    user_mod_notes: Mapped[List['User_Mod_Notes']] = db.relationship(
        back_populates='mod'
    )
    
    required_mods: Mapped[List['Mod']] = db.relationship(
        'Mod',
        secondary='mod_requirements',
        primaryjoin='Mod.id==mod_requirements.c.mod_id', 
        secondaryjoin='Mod.id==mod_requirements.c.required_mod_id', 
        back_populates='mods_that_require_this',
    )
    
    mods_that_require_this: Mapped[List['Mod']] = db.relationship(
        'Mod',
        secondary='mod_requirements',
        primaryjoin='Mod.id==mod_requirements.c.required_mod_id', 
        secondaryjoin='Mod.id==mod_requirements.c.mod_id', 
        back_populates='required_mods',
    )
    
    conflicting_mods: Mapped[List['Mod']] = db.relationship(
        'Mod',
        secondary='mod_conflicts',
        primaryjoin='Mod.id==mod_conflicts.c.conflicted_mod_id', 
        secondaryjoin='Mod.id==mod_conflicts.c.conflicting_mod_id', 
        back_populates='conflicted_mods',
    )

    conflicted_mods: Mapped[List['Mod']] = db.relationship(
        'Mod',
        secondary='mod_conflicts',
        primaryjoin='Mod.id==mod_conflicts.c.conflicting_mod_id', 
        secondaryjoin='Mod.id==mod_conflicts.c.conflicted_mod_id', 
        back_populates='conflicting_mods',
    )

    def check_conflicts(self, mlist_dot_mods):
        """Does this mod conflict with any mods in `mlist_dot_mods`? 
        
        Returns list of mods: [{mod},{mod}] or None
        """
        con_mods = []

        if self.conflicted_mods:
            con_mods = [mod for mod in self.conflicted_mods if mod in mlist_dot_mods]
        if self.conflicting_mods:
            con_mods.extend([mod for mod in self.conflicting_mods if mod in mlist_dot_mods and mod not in con_mods])

        if len(con_mods) >= 1:
            return con_mods

        return None

    def check_requirements(self, mlist_dot_mods):
        """Does this list have all the requirements stored for this mod?
        
        Returns list of required mods not in the list: [{mod},{mod}] or None
        """

        if self.required_mods:
            req_mods = [mod for mod in self.required_mods if mod not in mlist_dot_mods]

            if len(req_mods) >= 1:
                return req_mods

        return None

    def get_notes_by(self, author):
        """Returns 'notes' str from User_Mod_Notes obj associated 
        with both this mod and author(user)"""

        if self.user_mod_notes:
            notes = [(UMNote.notes for UMNote in self.user_mod_notes if UMNote.user == author)]

            return notes[0]
        
        return None

    def __repr__(self):
        return f'<Nexus Mod #{self.id}: "{self.name}" for "{self.for_game.name}"\nDescription: {self.summary}>'


# A game for which Nexus hosts mods.
class Game(db.Model):

    __tablename__ = 'games'

    # ID in this model must match Nexus game ID
    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=False
    )

    # slug of game name used by Nexus for game page url
    domain_name: Mapped[str]

    # full name of game on Nexus (w/ caps & spaces)
    name: Mapped[str]

    subject_of_modlists: Mapped[List["Modlist"]] = db.relationship(back_populates='for_game')

    subject_of_mods: Mapped[List['Mod']] = db.relationship(
        secondary=game_mod, 
        back_populates='for_games')

    def __repr__(self):
        return f'<Game #{self.id}: "{self.name}">'


# User in the system.
class User(db.Model):

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    username: Mapped[str] = mapped_column(db.String(30))

    email: Mapped[str] = mapped_column(db.String(30))

    password: Mapped[str] = mapped_column(db.Text)

    is_admin: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=False
    )

    is_moderator: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=False
    )

    hide_nsfw: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=True
    )

    # modlists made/owned by the user
    modlists: Mapped[List['Modlist']] = db.relationship(
        back_populates='user',
        cascade='all, delete',
        passive_deletes=True,
    )

    # modlists the user follows
    followed_modlists: Mapped[List['Modlist']] = db.relationship(
        secondary='follow_modlist',
        back_populates='followers'
    )

    # List of Mods user has taken notes about, bypassing the `User_Mod_notes` class
    mods_with_notes: Mapped[List['Mod']] = db.relationship(
        secondary='user_mod_connection', 
        back_populates='users_with_notes',
        viewonly=True
    )

    # List of 'User_Mod_Notes' objects for 
    #   User -> User_Mod_Notes -> Mod associated with this user 
    # Each 'User_Mod_Notes' contains 'notes' by 'user' about 'mod'
    user_mod_notes: Mapped[List['User_Mod_Notes']] = db.relationship(
        back_populates='user'
    )

    #  mods user is actually using Nexus Tracking for
    keep_tracked = db.relationship(
        'Mod',
        secondary='keep_tracked'
    )

    # profiles this user follows
    followed_profiles: Mapped[List["User"]] = db.relationship(
        'User',
        secondary='follow_user',
        primaryjoin=(follow_user.c.user_id == id),
        secondaryjoin=(follow_user.c.followed_profile_id == id), 
        back_populates='followers',
    )

    # profiles that follow this user
    followers = db.relationship(
        'User',
        secondary='follow_user',
        primaryjoin=(follow_user.c.followed_profile_id == id),
        secondaryjoin=(follow_user.c.user_id == id), 
        back_populates='followed_profiles',
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

    def get_users_games(self):
        """Get list of games the user has made 
        lists for (probably owns the game)"""

        found_games = [mlist.game for mlist in self.modlists if mlist.game not in found_games]

        return found_games

    def get_notes_for(self, mod):
        """Returns 'notes' str from User_Mod_Notes obj associated 
        with both this mod and author(user)"""

        if self.user_mod_notes:
            notes = [(UMNotes.notes for UMNotes in self.user_mod_notes if UMNotes.mod == mod)]

            return notes[0]
        
        return None

    @classmethod
    def signup(cls, username, email, password):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd
        )

        db.session.add(user)
        return user

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"





def connect_db(app):
    """Connect this database to provided Flask app.

    Call this in the Flask app.
    """

    db.app = app
    db.init_app(app)