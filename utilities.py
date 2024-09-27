"""Helper functions for app.py

Covers logic functions and interactions 
with PostgreSQL database"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import insert
from app import db
from models import User, Modlist, Mod, Game, game_mod


def get_all_games_db():
    """Retrieves full list of game data from db.
    
    Returns games list from db if successful, or Exception details."""

    try:
        ordered_games = db.session.scalars(db.select(Game).order_by(Game.downloads.desc())).all()

    except Exception as e:
        print("Error querying db get_all_games(): ", e)
        return e

    return ordered_games


def get_game_db(game_domain_name):
    """Uses game_domain_name to retrieve game data from db.
    
    Returns Game object from db if successful, or Exception details."""

    game = db.session.scalars(db.select(Game).where(Game.domain_name==game_domain_name)).first()

    return game


def get_mod_db(mod_id):
    """Uses mod_id to retrieve mod data from db.
    
    Returns Mod object from db if successful, or None."""

    mod = db.session.get(Mod, mod_id)

    return mod


def get_user_modlists_db(user_id):
    """Uses user_id to retrieve modlist data from db.
    
    Returns Mod object from db if successful, or None."""

    modlists = db.session.scalars(db.select(Modlist).where(Modlist.user_id==user_id).order_by(Modlist.name)).all()

    return modlists


def filter_nxs_data(data_list, list_type):
    """Takes list of data from Nexus API call and 
    filters out unneeded data for db entry.

    Valid list types = 'games', 'mods'

    Returns db input ready data list."""

    db_ready_data = []

    if list_type == 'games':
        for game in data_list:
            db_ready_game = {
                'id':game['id'], 
                'domain_name':game['domain_name'],
                'name':game['name'],
                'downloads':game['downloads']
            }
            db_ready_data.append(db_ready_game)

    if list_type == 'mods':
        for mod in data_list:
            if mod['status'] == 'published':
                db_ready_mod = {
                    'id': mod['mod_id'], 
                    'name': mod['name'], 
                    'summary': mod['summary'],
                    'is_nsfw': mod['contains_adult_content'],
                    'picture_url': mod['picture_url']
                }
                if db_ready_mod['picture_url'] == None:
                    db_ready_mod['picture_url'] = 'https://upload.wikimedia.org/wikipedia/commons/b/b1/Missing-image-232x150.png'
                db_ready_data.append(db_ready_mod)

    return db_ready_data


def filter_nxs_mod_page(nexus_mod, game_obj):
    """Takes mod data object from Nexus API call and 
    filters out unneeded data to display on mod page.

    If mod is published, returns data to pass to mod html page.
    
    Data includes: 'id', 'name', 'summary', 'description', 
        'picture_url', 'version', 'endorsement_count', 
        'last_updated', 'author_name', 'author_handle', 
        'author_url', 'nsfw', 'user_endorsed'
    """

    if nexus_mod['status'] != 'published':
        return 

    formatted_time = format_time(nexus_mod['updated_time'])

    page_ready_mod = {
        'id': nexus_mod['mod_id'], 
        'name': nexus_mod['name'], 
        'summary': nexus_mod['summary'],
        'picture_url': nexus_mod['picture_url'],
        'version': nexus_mod['version'],
        'endorsement_count': nexus_mod['endorsement_count'],
        'last_updated': formatted_time,
        'author_name': nexus_mod['author'],
        'author_handle': nexus_mod['uploaded_by'],
        'author_url': nexus_mod['uploaded_users_profile_url'],
        'is_nsfw': nexus_mod['contains_adult_content'],
        'user_endorsed': nexus_mod['endorsement']['endorse_status']
    }

    if type(game_obj) == Exception or None:
        raise AttributeError

    if page_ready_mod['picture_url'] == None:
        page_ready_mod['picture_url'] = 'https://upload.wikimedia.org/wikipedia/commons/b/b1/Missing-image-232x150.png'

    return page_ready_mod


def format_time(updated_time):
    """Takes time from Nexus API call and formats it
    to yyyy-mm-dd, hh:mm (am/pm)"""

    edited_datetime = updated_time.replace('T', ', ')[:-13]
    if int(edited_datetime[12:13]) < 12:
        formatted_time = edited_datetime + " AM"
    else:
        formatted_time = edited_datetime + " PM"
    if edited_datetime[12]=='0':
        formatted_time = edited_datetime[:12] + edited_datetime[13:]


def update_all_games_db(db_ready_games):
    """Takes updated list of Nexus game data and 
    updates the stored db values.
    
    Returns True if successful, or Exception details."""

    try:
        stmt = insert(Game).values(db_ready_games)
        stmt = stmt.on_conflict_do_update(
            constraint="games_pkey",
            set_={
                'id': stmt.excluded.id,
                'domain_name': stmt.excluded.domain_name,
                'name': stmt.excluded.name,
                'downloads': stmt.excluded.downloads
            }
        )
        db.session.execute(stmt)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Error updating db: ", e)
        return e
        
    return True


def update_list_mods_db(db_ready_mods, game):
    """Takes list of mod data that has been filtered 
    to only contain: 'id', 'name', 'summary', 'is_nsfw', 'picture_url'
    
    Returns True if successful, or Exception details."""

    stmt = insert(Mod).values(db_ready_mods)
    stmt = stmt.on_conflict_do_update(
        constraint="mods_pkey",
        set_={
            'id': stmt.excluded.id,
            'name': stmt.excluded.name,
            'summary': stmt.excluded.summary,
            'is_nsfw': stmt.excluded.is_nsfw,
            'picture_url': stmt.excluded.picture_url
        }
    )

    db.session.execute(stmt)

    db.session.commit()
            
    return True


def link_mods_to_game(db_ready_mods, game):
    """Connects a mod to the game for which it was made.
    Access mod from game obj: 'subject_of_mods'
    Access game from mod obj: 'for_games'
    """

    for m in db_ready_mods:
        mod = get_mod_db(m['id'])
        
        if mod not in game.subject_of_mods:
            game.subject_of_mods.append(mod)

    db.session.commit()


def add_mod_modlist_choices(user_id, mod):
    """Gets a user's modlists and filters out all modlists 
    that are not for the same game as the mod, or are 
    unassigned to a game.
    
    Returns list of game-matched or game-unassigned modlists."""

    modlists = get_user_modlists_db(user_id)

    users_modlist_choices = []

    for modlist in modlists:
        if len(modlist.for_games) == 0 or mod.for_games[0] == modlist.for_games[0]:
            users_modlist_choices.append(modlist)

    return users_modlist_choices


def get_recent_modlists_by_game(user_id):
    """Get list of user's modlists ordered by last_updated
    and grouped by game. Also indicates privacy status of all 
    modlists for each game - if all modlists are marked as 
    private, entire game will not be shown on public profile page.
    
    Return list of games and mods:
    [{'game':game, 'all_private':bool, 'modlists':[modlist, modlist]}]"""

    user = db.session.scalars(db.select(User).where(User.id==user_id)).first()

    all_recent_modlists = db.session.scalars(db.select(Modlist).options(db.selectinload(Modlist.user)).order_by(Modlist.last_updated.desc())).all()

    return_list = order_modlists_by_game(all_recent_modlists)

    return return_list


def get_public_modlists_by_game(user_id):
    """Get list of user's modlists ordered by last_updated
    and grouped by game, with all empty and private content 
    removed.
    
    Return list of games and mods:
    [{'game':game, 'modlists':[modlist, modlist]}]"""

    user = db.session.scalars(db.select(User).where(User.id==user_id)).first()

    recent_public_modlists = db.session.scalars(db.select(Modlist).options(db.selectinload(Modlist.user)).filter_by(private=False).order_by(Modlist.last_updated.desc())).all()

    return_list = order_modlists_by_game(recent_public_modlists)

    for game in return_list:
        del game['all_private']

    return return_list


def order_modlists_by_game(modlist_list):
    """Take a list of modlists and return them ordered by game.
    Order from modlist_list will be respected - first modlist's 
    game will be first game in list of games. Also indicates 
    privacy status of all modlists for each game.
    
    Return list of games and mods:
    [{'game':game, 'all_private':bool, 'modlists':[modlist, modlist]}]"""

    return_list = []
    recent_games = []
    all_private = True

    for modlist in modlist_list:
         if modlist.for_games != [] and modlist.for_games[0].id not in [game.id for game in recent_games]:
            recent_games.append(modlist.for_games[0])

    for game in recent_games:
        print("game in users_games: ", game)
        game_modlists = {'game':game, 'modlists':[]}
        for modlist in modlist_list:
            if len(modlist.for_games) != 0 and modlist.for_games[0].id == game.id:
                game_modlists['modlists'].append(modlist)
                if modlist.private == False:
                    all_private = False
        game_modlists['all_private'] = all_private
        return_list.append(game_modlists)

    return return_list


def get_empty_modlists(user_id):
    """Get list of user's modlists that are not 
    assigned to a game and contain no mods.
    
    Return list of empty modlists:
    [modlist, modlist]"""

    user = db.session.scalars(db.select(User).where(User.id==user_id)).first()

    recent_modlists = db.session.scalars(db.select(Modlist).options(db.selectinload(Modlist.user)).order_by(Modlist.last_updated.desc())).all()

    return_list = []

    for modlist in recent_modlists:
        if len(modlist.for_games) == 0:
            return_list.append(modlist)

    return return_list