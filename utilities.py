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
        print("Error querying db: ", e)
        return e

    return ordered_games


def filter_nxs_data(data_list, list_type, game_obj=None):
    """Takes list of data from Nexus API call and 
    filters out unneeded data for db entry.

    Valid list types = 'game', 'mod'

    Returns db input ready data list."""

    db_ready_data = []
    print("================ starting filter_nxs_data() ================")
    if list_type == 'game':
        for game in data_list:
            db_ready_game = {
                'id':game['id'], 
                'domain_name':game['domain_name'],
                'name':game['name'],
                'downloads':game['downloads']
            }
            db_ready_data.append(db_ready_game)

    if list_type == 'mod':
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
                db_ready_mod['for_games'] = game_obj
                db_ready_data.append(db_ready_mod)

    return db_ready_data


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