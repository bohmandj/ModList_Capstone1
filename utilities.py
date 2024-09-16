"""Helper functions for app.py

Covers logic functions and interactions 
with PostgreSQL database"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import insert
from app import db
from models import User, Modlist, Mod, Game


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

    try:
        result = db.session.scalars(db.select(Game).where(Game.domain_name==game_domain_name)).first()
        print(f'''
        
        [[[[[[[[[[[[[[[[[[[[[[get_game_db() returns]]]]]]]]]]]]]]]]]]]]]]
        result.first(): {result}
        result.first().name: {result.name}
        
        ''')

    except Exception as e:
        print("Error querying db get_game_db(): ", e)
        return e

    else:
        game = result

    return game


def get_mod_db(mod_id):
    """Uses mod_id to retrieve mod data from db.
    
    Returns Mod object from db if successful, or None."""

    try:
        mod = db.session.get(Mod, mod_id)
        print(f'''
        
        [[[[[[[[[[[[[[[[[[[[[[get_mod_db() returns]]]]]]]]]]]]]]]]]]]]]]
        mod: {result}
        mod.name: {result.name}
        
        ''')

    except Exception as e:
        print("Error querying db get_mod_db(): ", e)
        return None

    return mod


def filter_nxs_data(data_list, list_type, game_obj):
    """Takes list of data from Nexus API call and 
    filters out unneeded data for db entry.

    Valid list types = 'games', 'mods'

    Returns db input ready data list."""

    db_ready_data = []
    print(f"================ starting filter_nxs_data() ================  GAME OBJ: {game_obj.name} // {type(game_obj)}")
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
                    'picture_url': mod['picture_url']
                }
                if type(game_obj) == Exception or None:
                    raise AttributeError
                if db_ready_mod['picture_url'] == 'null':
                    print(f'''
                    
                    
                    filter_nxs_data() PICTURE URL:
                    {db_ready_mod['picture_url']}
                    
                    
                        ''')
                    db_ready_mod['picture_url'] = 'https://upload.wikimedia.org/wikipedia/commons/b/b1/Missing-image-232x150.png'
                db_ready_mod['for_games'] = game_obj
                db_ready_data.append(db_ready_mod)

    return db_ready_data


def filter_nxs_mod(nexus_mod, game_obj):
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
        'nsfw': nexus_mod['contains_adult_content'],
        'user_endorsed': nexus_mod['endorsement']['endorse_status']
    }

    if type(game_obj) == Exception or None:
        raise AttributeError

    if page_ready_mod['picture_url'] == 'null':
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


def update_mod_db():
    """"""

    db_mod = get_mod_db()

    if db_mod:
        print("is db_mod, yay!")
        # update mod in db
    else:
        print("is NOT db_mod, boo!")
        # insert mod to db

    return db_mod