"""Helper functions for app.py

Covers logic functions and interactions 
with PostgreSQL database"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import insert
from flask import flash, g
from app import db
from models import User, Modlist, Mod, Game, game_mod, keep_tracked, modlist_mod
from nexus_api import get_mod_nxs, get_tracked_mods_nxs
from time import sleep


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


def get_tracked_modlist_db(user_id, load_mods=False):
    """Gets the user's Nexus Tracked Mods modlist from the db.
    
    Returns tracked modlist or the modlist with mods eager loaded if load_mods=True is passed."""

    if load_mods:
        stmt = (
            db.select(Modlist)
            .options(db.joinedload(Modlist.mods))  # Eager load mods
            .where(Modlist.user_id == user_id)
            .where(Modlist.name == "Nexus Tracked Mods")
        )
    else:
        stmt = (
            db.select(Modlist)
            .where(Modlist.user_id == user_id)
            .where(Modlist.name == "Nexus Tracked Mods")
        )
    
    tracked_modlist = db.session.execute(stmt).scalars().first()

    return tracked_modlist


def get_tracked_mods_db(user_id, just_ids=False, order='updated'):
    """Gets list of tracked mods or mod ids from the user's 
    Nexus Tracked Mods modlist stored in the db.
    
    Returns a list of user's keep_tracked mods or the mods' IDs 
    based on whether the optional just_ids flag is True. Parameter 
    'order' sets the order in which mods are returned - 'name' or 
    'author' returns in alphabetical order of that attribute, otherwise
    mods are returned in order of most recently updated first."""

    if order == 'name':
        order = Mod.name
    elif order == 'author':
        order = Mod.uploaded_by
    else:
        order = Mod.updated_timestamp.desc()
    
    if just_ids:
        stmt = (
            db.select(Mod.id)
            .join(Modlist.mods)
            .where(Modlist.name == "Nexus Tracked Mods")
            .where(Modlist.user_id == user_id)
            .order_by(order)
        )
    else:
        stmt = (
            db.select(Mod)
            .join(Modlist.mods)
            .where(Modlist.name == "Nexus Tracked Mods")
            .where(Modlist.user_id == user_id)
            .order_by(order)
        )

    tracked_mods = db.session.execute(stmt).scalars().all()

    return tracked_mods


def get_keep_tracked_mods_db(user_id, just_ids=False, order='updated'):
    """Gets list of user's keep_tracked mods or mod ids 
    from the database.
    
    Returns a list of user's keep_tracked mods or the mods' IDs 
    based on whether the optional just_ids flag is True. Parameter 
    'order' sets the order in which mods are returned - 'name' or 
    'author' returns in alphabetical order of that attribute, otherwise
    mods are returned in order of most recently updated first."""

    if order == 'name':
        order = Mod.name
    elif order == 'author':
        order = Mod.uploaded_by
    else:
        order = Mod.updated_timestamp.desc()
    
    if just_ids:
        stmt = (
            db.select(Mod.id)
            .join(keep_tracked)
            .where(keep_tracked.c.user_id == user_id)
            .order_by(order)
        )
    else:
        stmt = (
            db.select(Mod)
            .join(keep_tracked)
            .where(keep_tracked.c.user_id == user_id)
            .order_by(order)
        )
    
    keep_tracked_mods = db.session.execute(stmt).scalars().all()

    return keep_tracked_mods


def get_tracked_not_keep_db(user_id, just_ids=False, order='updated'):
    """Gets list of user's tracked mods, with the mods marked 
    'keep_tracked' removed from the list.
    
    Returns a list of user's non-keep_tracked tracked mods, 
    or the mods' IDs based on whether the optional just_ids 
    flag is True. Parameter 
    'order' sets the order in which mods are returned - 'name' or 
    'author' returns in alphabetical order of that attribute, otherwise
    mods are returned in order of most recently updated first."""

    all_tracked_mods = get_tracked_mods_db(user_id, order=order)

    keep_tracked_ids = get_keep_tracked_mods_db(user_id, just_ids=True, order=order)

    return_tracked_mods = []

    # remove keep_tracked from all_tracked
    for mod in all_tracked_mods:
        if mod.id not in keep_tracked_ids:
            return_tracked_mods.append(mod)

    return return_tracked_mods


def paginate_tracked_mods(user_id, page=1, per_page=25, order='update', tab='tracked-mods'):
    """Gets the user's Nexus Tracked Mods excluding their keep tracked mods with pagination."""

    if order == 'name':
        order = Mod.name
    elif order == 'author':
        order = Mod.uploaded_by
    else:
        order = Mod.updated_timestamp.desc()
        
    # Get the user's Nexus Tracked Mods modlist
    tracked_modlist = get_tracked_modlist_db(user_id, load_mods=False)

    if not tracked_modlist:
        Modlist.new_modlist(
            name='Nexus Tracked Mods', 
            description="This modlist automatically populates with all the mods in your Nexus account's Tracking Centre.", 
            private=True,
            user=g.user
        )
        db.session.commit()
        tracked_modlist = get_tracked_modlist_db(user_id, load_mods=False)

    if tab == 'keep-tracked-mods':
        # Query to get the keep tracked mods
        mods_stmt = (
            db.select(Mod)
            .join(keep_tracked)
            .where(keep_tracked.c.user_id == user_id)
            .order_by(order)
        )
    else:
        # Get the IDs of the mods that the user has marked as keep tracked
        keep_tracked_mod_ids = get_keep_tracked_mods_db(user_id, just_ids=True)

        # Query to get the tracked mods, excluding the keep tracked mods
        mods_stmt = (
           db.select(Mod)
            .join(modlist_mod)
            .where(modlist_mod.c.modlist_id == tracked_modlist.id)
            .where(Mod.id.notin_(keep_tracked_mod_ids))
            .order_by(order)
        )

    # Apply pagination
    paginated_mods = db.paginate(mods_stmt, page=page, per_page=per_page)

    return paginated_mods


def add_missing_tracked_mods_db(user_id, nexus_tracked_data):
    """Checks if there are any missing mods in the database 
    compared to fresh nexus_tracked_data argument, and calls 
    Nexus API to get the missing mod's data to add to the db.

    Note: function does not update user's Nexus Tracked 
    Mods modlist, only adds mods to db. Use 
    sync_tracked_modlist_mods_db(user_id, nexus_tracked_data) 
    to update modlist.
    
    Returns list of unpublished ids that should not get sync'd 
    in user's modlist.
    """

    current_tracked_ids = get_tracked_mods_db(user_id, just_ids=True)

    nexus_tracked_ids_by_game = group_nexus_tracked_by_game(nexus_tracked_data)

    nxs_req_limit = 25 # Nexus API throws error for >30 requests/sec.
    counter = 0

    unpublished_ids = []

    for domain_name in nexus_tracked_ids_by_game:

        game = db.session.scalars(db.select(Game).where(Game.domain_name==domain_name)).first()

        nexus_data_to_add = []

        for id in nexus_tracked_ids_by_game[domain_name]:
            if id not in current_tracked_ids:
                counter += 1
                try:
                    new_nexus_data = get_mod_nxs(game, id)
                except Exception as e:
                    print('Error in get_mod_nxs(): ', e)
                    flash(f"Error was encountered retrieving data from Nexus Tracking Centre for mod #{id}.\nVisit your Nexus Tracked Mods modlist to reattempt data retrieval.", "warning")
                    if counter >= nxs_req_limit:
                        counter = 0
                        break
                else:
                    if new_nexus_data['status']=='published':
                        nexus_data_to_add.append(new_nexus_data)
                    else:
                        unpublished_ids.append(id)
                        flash(f"Mod #{id}'s status is not set to 'published', so we were unable to import its data from Nexus.", "warning")
                
                if counter >= nxs_req_limit:
                    sleep(1)
                    counter = 0

        if len(nexus_data_to_add) == 0:
            continue
        
        db_ready_mods = filter_nxs_data(nexus_data_to_add, 'mods')

        update_all_games_db_resp = update_list_mods_db(db_ready_mods, game)
        link_mods_to_game(db_ready_mods, game)

    return unpublished_ids


def group_nexus_tracked_by_game(nexus_tracked_data):
    """Search db for all games with mods in nexus_tracked_data.
    Return an object containing keys = domain_names from 
    nexus_tracked_data, with a value of a list of the ids of 
    the tracked mods for the game with that domain name.
        Example return object: 
        {'domain_name': [mod_id, mod_id]}
    """
    
    return_obj = {}

    for data in nexus_tracked_data:
        if data['domain_name'] not in return_obj:
            return_obj[data['domain_name']] = []

        return_obj[data['domain_name']].append(data['mod_id'])
    
    return return_obj


def sync_tracked_modlist_mods_db(user_id, nexus_tracked_data, unpublished_ids):
    """If a mod is included in the passed-in Nexus API tracked-mods 
    call response but not in user's Nexus Tracked Mods modlist, the 
    mods is queried from the db and added to the modlist.
    
    Necessary when mods are added to the Tracking Center on 
    Nexus' site, not through ModList site."""

    tracked_modlist = get_tracked_modlist_db(user_id, load_mods=True)

    nxs_tracked_mod_ids = []
    # remove unpublished mods from list of tracked mod ids
    for data in nexus_tracked_data:
        if data['mod_id'] not in unpublished_ids:
            nxs_tracked_mod_ids.append(data['mod_id'])

    # add tracked mods from Nexus to tracked_modlist if missing
    for id in nxs_tracked_mod_ids:
        if id not in [mod.id for mod in tracked_modlist.mods]:
            mod_to_add = db.get_or_404(Mod, id)
            tracked_modlist.mods.append(mod_to_add)

    # remove mods from tracked_modlist if not tracked on Nexus
    for mod in tracked_modlist.mods:
        if mod.id not in nxs_tracked_mod_ids:
            tracked_modlist.mods.remove(mod)

    db.session.commit()


def update_tracked_mods_from_nexus(user_id):
    """Do Nexus API call to get mods currently in Nexus Tracking Centre. Use that mod data to update database with any mods tracked on Nexus that are not yet in the db. Use the currently tracked list to update user's Nexus Tracked Mods modlist with mod data in db (add missing mods & remove mods that shouldn't be there).
    
    Flash error messages to user if issues arise. Return nothing.
    Call this aggregate function from app.py."""
    try:
        nexus_tracked_data = get_tracked_mods_nxs()
        unpublished_ids = add_missing_tracked_mods_db(user_id, nexus_tracked_data)
    except Exception as e:
        print('get_tracked_mods_nxs() or\nadd_missing_tracked_mods_db() Error:\n    ', e)
        flash("Problem occurred retrieving tracked mods from Nexus Tracking Centre.\nClick 'Re-Sync with Nexus Tracking Centre' button on your Nexus Tracked Mods modlist to reattempt.", "danger")
        raise e
    else:
        try:
            sync_tracked_modlist_mods_db(user_id, nexus_tracked_data, unpublished_ids)
        except Exception as e:
            print('sync_tracked_modlist_mods_db() Error:\n  ', e)
            flash(f"Error was encountered syncing mods in your Nexus Tracked Mods modlist to the official Nexus Tracking Centre records.\nIf mods displayed in your Nexus Tracked Mods modlist are inaccurate, click 'Re-Sync with Nexus Tracking Centre' button to reattempt sync.", "warning")


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
            if mod['status'] == 'published' and type(mod['mod_id']):
                db_ready_mod = {
                    'id': mod['mod_id'], 
                    'name': mod['name'], 
                    'summary': mod['summary'],
                    'is_nsfw': mod['contains_adult_content'],
                    'name': mod['name'], 
                    'picture_url': mod['picture_url'],
                    'updated_timestamp': mod['updated_timestamp'],
                    'uploaded_by': mod['uploaded_by']
                }
                if db_ready_mod['picture_url'] == None:
                    db_ready_mod['picture_url'] = 'None'
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
        page_ready_mod['picture_url'] = 'None'

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
        print("update_all_games_db() Error:\n   ", e)
        return e
        
    return True


def update_list_mods_db(db_ready_mods, game):
    """Takes list of mod data that has been filtered 
    to only contain: 'id', 'name', 'summary', 'is_nsfw', 'picture_url', 'updated_timestamp', 'uploaded_by'
    
    Returns True if successful, or Exception details."""

    try:
        stmt = insert(Mod).values(db_ready_mods)
        stmt = stmt.on_conflict_do_update(
            constraint="mods_pkey",
            set_={
                'id': stmt.excluded.id,
                'name': stmt.excluded.name,
                'summary': stmt.excluded.summary,
                'is_nsfw': stmt.excluded.is_nsfw,
                'picture_url': stmt.excluded.picture_url,
                'updated_timestamp': stmt.excluded.updated_timestamp,
                'uploaded_by': stmt.excluded.uploaded_by
            }
        )

        db.session.execute(stmt)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("update_list_mods_db() Error:\n   ", e)
        raise e
        # return e
            
    return True


def link_mods_to_game(db_ready_mods, game):
    """Connects a mod to the game for which it was made.
    Access mod from game obj: 'subject_of_mods'
    Access game from mod obj: 'for_games'
    """

    try:
        for m in db_ready_mods:
            mod = db.get_or_404(Mod, m['id'])
            
            if mod not in game.subject_of_mods:
                game.subject_of_mods.append(mod)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("link_mods_to_game() Error:\n ", e)


def add_mod_modlist_choices(user_id, mod):
    """Gets a user's modlists and filters out all modlists 
    that are not for the same game as the mod, or are 
    unassigned to a game.
    
    Returns list of game-matched or game-unassigned modlists."""

    modlists = db.session.scalars(db.select(Modlist).where(Modlist.user_id==user_id).order_by(Modlist.name)).all()

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

    all_recent_modlists = db.session.scalars(db.select(Modlist).join(Modlist.user.and_(User.id == user_id)).order_by(Modlist.last_updated.desc())).all()

    return_list = order_modlists_by_game(all_recent_modlists)

    return return_list


def get_public_modlists_by_game(user_id):
    """Get list of user's modlists ordered by last_updated
    and grouped by game, with all empty and private content 
    removed.
    
    Return list of games and mods:
    [{'game':game, 'modlists':[modlist, modlist]}]"""

    recent_public_modlists = db.session.scalars(db.select(Modlist).filter_by(private=False).join(Modlist.user.and_(User.id == user_id)).order_by(Modlist.last_updated.desc())).all()

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

    recent_modlists = db.session.scalars(db.select(Modlist).join(Modlist.user.and_(User.id == user_id)).order_by(Modlist.name)).all()

    return_list = []

    for modlist in recent_modlists:
        if len(modlist.for_games) == 0 and modlist.name != 'Nexus Tracked Mods':
            return_list.append(modlist)

    return return_list


def check_modlist_editable(user_id, modlist, g_user_id, ):
    """Determine if selected modlist is a invalid modlist for 
    the user to edit. A user can NOT edit a modlist if the 
    modlist does not belong to the signed in user, or if the 
    modlist is named 'Nexus Tracked Mods'.

    Returns False if modlist is editable, or the message to 
    flash if it can not be edited by the signed-in user user."""

    if modlist.user_id != int(g_user_id) or int(user_id) != int(g_user_id):
        return "A modlist can only be edited by the owner of the modlist."

    elif modlist.name == 'Nexus Tracked Mods':
        return "The 'Nexus Tracked Mods' modlist is not editable."

    else:
        return False