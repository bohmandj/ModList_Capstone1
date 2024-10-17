"""Helper functions for app.py

Covers logic functions and interactions 
with PostgreSQL database"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import insert
from flask import flash, g, abort
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
        print("Page: Homepage\nFunction: get_all_games_db()\nQuery failed to retrieve all game data from db; error: ", e)
        return e

    return ordered_games


def get_game_db(game_domain_name):
    """Uses game_domain_name to retrieve game data from db.
    
    Returns Game object from db if successful, or Exception."""

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


def paginate_modlist_mods(user_id, modlist_id, page=1, per_page=25, order='update'):
    """Gets the user's modlist and the mods it contains."""

    if order == 'name':
        order = Mod.name
    elif order == 'author':
        order = Mod.uploaded_by
    else:
        order = Mod.updated_timestamp.desc()

    stmt = (
        db.session.query(Mod)
        .join(modlist_mod)
        .filter(modlist_mod.c.modlist_id == modlist_id)
        .order_by(order)
    )

    # Apply pagination
    paginated_mods = db.paginate(stmt, page=page, per_page=per_page)

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
    sleep_interval = 1 / nxs_req_limit

    get_mod_error_ids = []
    unpublished_ids = []

    for domain_name in nexus_tracked_ids_by_game:

        nexus_data_to_add = []

        for id in nexus_tracked_ids_by_game[domain_name]:
            if id not in current_tracked_ids:
                try:
                    sleep(sleep_interval)
                    new_nexus_data = get_mod_nxs(domain_name, id)
                except Exception as e:
                    print("Page: login() or Tracked Modlist page\nFunction: get_mod_nxs() in add_missing_tracked_mods_db()\nFailed to retrieve Nexus API data, error: ", e)
                    get_mod_error_ids.append(id)
                else:
                    if new_nexus_data['status']=='published':
                        nexus_data_to_add.append(new_nexus_data)
                    else:
                        unpublished_ids.append(id)
            
        if len(nexus_data_to_add) == 0:
            continue

        game = get_game_db(domain_name)
        if not game:
            continue
        
        db_ready_mods = filter_nxs_data(nexus_data_to_add, 'mods')

        update_all_games_db_resp = update_list_mods_db(db_ready_mods, game)
        link_mods_to_game(db_ready_mods, game)

    if len(get_mod_error_ids) != 0:
        flash(f"An error was encountered retrieving data from Nexus Tracking Centre for tracked mods with these IDs: {str(get_mod_error_ids)[1:-1]}.\nVisit your Nexus Tracked Mods modlist and use the 'Re-Sync Tracked Mods to Nexus' button to reattempt data retrieval.", "warning")
    if len(unpublished_ids) != 0:
        flash(f"Tracked mods with these IDs: {str(unpublished_ids)[1:-1]} have a status that is not set to 'published'.\nWe did not import data from Nexus for any unpublished mods.", "warning")

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
            mod_to_add = db.get(Mod, id)
            if mod_to_add != None:
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
        print("Page: login() or Tracked Mods page\nFunction:\n____get_tracked_mods_nxs(), or\n____add_missing_tracked_mods_db()\n____in update_tracked_mods_from_nexus()\nFailed to retrieve Nexus API data, error: ", e)
        flash("A problem occurred while retrieving your tracked mods from the Tracking Centre on Nexus.\nClick 'Re-Sync with Nexus Tracking Centre' button on your Nexus Tracked Mods modlist to reattempt sync.", "danger")
    else:
        try:
            sync_tracked_modlist_mods_db(user_id, nexus_tracked_data, unpublished_ids)
        except Exception as e:
            print('sync_tracked_modlist_mods_db() Error:\n  ', e)
            flash(f"An error was encountered syncing mods in your Nexus Tracked Mods modlist to the official Nexus Tracking Centre records.\nIf mods displayed in your Nexus Tracked Mods modlist are inaccurate, click 'Re-Sync with Nexus Tracking Centre' button to reattempt sync.", "warning")


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


def filter_nxs_mod_page(nexus_mod):
    """Takes mod data object from Nexus API call and 
    filters out unneeded data to display on mod page.

    If mod is published, returns data to pass to mod html page.
    
    Data includes: 'id', 'name', 'summary', 'description', 
        'picture_url', 'version', 'endorsement_count', 
        'last_updated', 'author_name', 'author_handle', 
        'author_url', 'nsfw', 'user_endorsed'
    """

    if nexus_mod['status'] != 'published':
        description = f"The requested mod's status is listed as '{nexus_mod['status']}', so available data may be incomplete.\nMod can not be displayed."
        abort(500, description) 

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
        print("Page: login()\nFunction: update_all_games_db()\nFailed to commit inserts/updates to games in db, error: ", e)
        return e
        
    return True


def update_list_mods_db(db_ready_mods):
    """Takes list of mod data that has been filtered 
    to only contain: 'id', 'name', 'summary', 'is_nsfw', 'picture_url', 'updated_timestamp', 'uploaded_by' and inserts or updates each mod
    from the list in the db.
    
    Returns True if successful, or raises Exception details."""

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
        print("Page: Game page or Mod page\nFunction: update_list_mods_db() in:\n____add_missing_tracked_mods_db(), or in\n____Game or Mod page routes\nFailed to retrieve Nexus API data, error: ", e)
        raise e
            
    return True


def link_mods_to_game(db_ready_mods, game):
    """Connects a mod to the game for which it was made.
    Access mod from game obj: 'subject_of_mods'
    Access game from mod obj: 'for_games'

    Returns nothing -> adds mod in game.subject_of_mods to 
    be committed after the function, or raises Exception.
    """

    for m in db_ready_mods:
        mod = db.session.scalars(db.select(Mod).where(Mod.id==m['id'])).first()

        if mod and mod not in game.subject_of_mods:
            game.subject_of_mods.append(mod)



def add_mod_modlist_choices(user_id, mod):
    """Gets a user's modlists and filters out all modlists 
    that are not for the same game as the mod, or are 
    unassigned to a game.
    
    Returns object containing a list of game-matched or 
    game-unassigned modlists to show as options for the 
    to-be-added mod, and a list of modlists belonging to 
    the user that already contain the to-be-added mod.

    Example: 
    {'users_modlist_choices':[modlist, modlist], 
    'modlists_w_mod':[modlist, modlist]}"""

    modlists = db.session.scalars(db.select(Modlist).where(Modlist.user_id==user_id).order_by(Modlist.name)).all()

    users_empty_modlist_choices = []
    users_modlist_choices = []
    modlists_w_mod = []

    for modlist in modlists:
        if modlist.name == "Nexus Tracked Mods":
            continue

        if modlist.id in [modlist.id for modlist in mod.in_modlists]:
            modlists_w_mod.append(modlist)
            continue

        if len(modlist.for_games) == 0:
            users_empty_modlist_choices.append(modlist)
            continue

        for game in mod.for_games:
            if game in modlist.for_games:
                users_modlist_choices.append(modlist)
                break

    return_obj = {'users_empty_modlist_choices':users_empty_modlist_choices, 'users_modlist_choices':users_modlist_choices, 'modlists_w_mod':modlists_w_mod}

    return return_obj


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


def check_modlist_uneditable(user_id, modlist, g_user_id, ):
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