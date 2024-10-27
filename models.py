"""SQLAlchemy models for Capstone"""

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import List, Optional
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

bcrypt = Bcrypt()
db = SQLAlchemy(model_class=Base)

###########################################################
# Association Tables:

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
        db.ForeignKey(
            'modlists.id', 
            ondelete='CASCADE'
            ), 
        primary_key=True
        ),

    db.Column(
        'mod_id', 
        db.ForeignKey(
            'mods.id', 
            ondelete='CASCADE'
            ), 
        primary_key=True
        )
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


#Connection of a game to the modlist that is made for it.
game_modlist = db.Table(
    
    'game_modlist',
        
    db.Column(
        'modlist_id', 
        db.ForeignKey(
            'modlists.id', 
            ondelete='CASCADE'
            ), 
        primary_key=True
    ),

    db.Column(
        'game_id', 
        db.ForeignKey(
            'games.id', 
            ondelete='CASCADE'
            ), 
        primary_key=True
    )
)


###########################################################
# Model Classes:

# A list of game mods made by a user.
class Modlist(db.Model):

    __tablename__ = 'modlists'

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    name: Mapped[str] = mapped_column(db.Text)

    description: Mapped[Optional[str]]

    private: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=False
    )
    has_nsfw: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=False
    )

    last_updated: Mapped[datetime] = mapped_column(
        index=True, 
        default=lambda: datetime.now(timezone.utc)
    )

    mods: Mapped[List['Mod']] = db.relationship(
        secondary=modlist_mod,
        back_populates='in_modlists',
        passive_deletes=True
    )

    user_id: Mapped[int] = mapped_column(
        db.ForeignKey(
            'users.id', 
            ondelete='CASCADE'
        )
    )
    # user that made/owns the modlist
    user: Mapped['User'] = db.relationship(
        back_populates='modlists'
    )

    # game the modlist is built for
    for_games: Mapped[List['Game']] = db.relationship(
        secondary=game_modlist,
        back_populates='subject_of_modlists',
        passive_deletes=True
    )

    def update_mlist_tstamp(self):
        self.last_updated = datetime.now(timezone.utc)

    def assign_modlist_for_games(self, game):
        if game not in self.for_games:
            self.for_games.append(game)

    def mark_nsfw_if_nsfw(self, mod):
        if mod.is_nsfw:
            self.has_nsfw = True

    @classmethod
    def new_modlist(cls, name, description, private, user):
        modlist = Modlist(
                name=name,
                description=description,
                private=private,
                user=user
            )
        return modlist

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

    name: Mapped[str] = mapped_column(db.Text)

    summary: Mapped[str] = mapped_column(
        db.Text, 
        default=''
    )

    is_nsfw: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=False
    )

    picture_url: Mapped[str] = mapped_column(
        db.String, 
        default='https://upload.wikimedia.org/wikipedia/commons/b/b1/Missing-image-232x150.png'
    )

    updated_timestamp: Mapped[int] = mapped_column(db.BigInteger)

    uploaded_by: Mapped[str] = mapped_column(db.Text)

    in_modlists: Mapped[List['Modlist']] = db.relationship(
        secondary=modlist_mod, 
        back_populates='mods',
        passive_deletes=True
    )
    
    for_games: Mapped[List['Game']] = db.relationship(
        secondary=game_mod,
        back_populates='subject_of_mods',
        passive_deletes=True
    )

    def __repr__(self):
        if len(self.for_games) > 0:
            for_game = f' for "{self.for_games[0].name}"'
        else: 
            for_game = ""
        return f'<Nexus Mod #{self.id}: "{self.name}"{for_game}>'


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
    name: Mapped[str] = mapped_column(db.Text)

    downloads: Mapped[int] = mapped_column(db.BigInteger)

    subject_of_modlists: Mapped[List['Modlist']] = db.relationship(
        secondary=game_modlist,
        back_populates='for_games',
        passive_deletes=True
    )

    subject_of_mods: Mapped[List['Mod']] = db.relationship(
        secondary=game_mod, 
        back_populates='for_games',
        passive_deletes=True
    )

    def __repr__(self):
        return f'<Game #{self.id}: "{self.name}", #downloads:{self.downloads}>'


# User in the system.
class User(db.Model):

    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    username: Mapped[str] = mapped_column(
        db.String(30),
        unique=True
    )

    email: Mapped[str] = mapped_column(
        db.String(30),
        unique=True
    )

    password: Mapped[str] = mapped_column(db.Text)

    hide_nsfw: Mapped[bool] = mapped_column(
        db.Boolean, 
        default=True
    )

    # modlists made/owned by the user
    modlists: Mapped[List['Modlist']] = db.relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    #  mods user is actually using Nexus Tracking for
    keep_tracked = db.relationship(
        'Mod',
        secondary='keep_tracked'
    )

    def hash_new_password(cls, password):
        """Save a new password to the user's data in db.

        Hashes password and adds edited user to system.
        """

        try:
            hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
        except:
            hashed_pwd = None

        return hashed_pwd

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

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        It searches for a user whose username and password hash matches this 
        password and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """
        
        user = db.session.scalars(db.select(User).filter_by(username=username).limit(1)).first()
        
        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False



def connect_db(app):
    """Connect this database to provided Flask app.

    Call this in the Flask app.
    """

    db.app = app
    db.init_app(app)