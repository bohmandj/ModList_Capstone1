import requests
from flask import abort, flash, session
from flask_sqlalchemy import SQLAlchemy
from secretkeys import nexus_api_key
from app import db
from models import User, Modlist, Mod, Game

base_url = 'https://api.nexusmods.com'

def get_all_games_nxs(include_unapproved=False, headers=None):
    """Nexus API call.
    
    Returns games list from Nexus if successful, or Exception details.

    Game obj: {"id": int, "name": str, "forum_url": str, 
    "nexusmods_url": str, "genre": str, "file_count": int, 
    "downloads": int, "domain_name": int, "approved_date": int, 
    "file_views": int, "authors": int, "file_endorsements": int, 
    "mods": int, "categories": [ {"category_id": int, 
    "name": str, "parent_category": bool} ] }

    Optionally can also include unapproved games. ( include_unapproved=True )
    """

    url = f'{base_url}/v1/games.json'

    if include_unapproved:
        url += '?include_unapproved=true'

    res = requests.get(url, params=include_unapproved, headers=headers)
    nexus_games = res.json()

    return nexus_games


def get_mods_of_type_nxs(game, request_type, headers=None):
    """Nexus API call.
    
    Returns list of most recently added mods for provided 
    game on Nexus if successful, or Exception details.

    Valid request_type inputs: 
        'latest_added', 'latest_updated', 'trending'
    
    Example returned mod data: 
        { 'name': str, 'summary': str, 'description': str, 'picture_url': str, 
        'mod_downloads': num, 'mod_unique_downloads': num, 'uid': num, 
        'mod_id': num, 'game_id': num, 'allow_rating': true, 'domain_name': str, 
        'category_id': num, 'version': str(of int),	'endorsement_count': num, 
        'created_timestamp': num, 'created_time': datetime (str of int), 
        'updated_timestamp': num, 'updated_time': datetime (str of int), 
        'author': str, 'uploaded_by': str, 'uploaded_users_profile_url': str, 
        'contains_adult_content': bool, 'status': str - 'published' / 'not_published', 
        'available': bool, 'user': { 'member_id': num, 'member_group_id': num, 'name': str }, 
        'endorsement': null }
    """

    url = f'{base_url}/v1/games/{game.domain_name}/mods/{request_type}.json'

    try:
        res = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print("Page: Game page, Function: get_mods_of_type_nxs()\nFailed to retrieve Nexus API data, error: ", e)
        return 'error'

    nexus_mods = res.json()

    return nexus_mods


def get_mod_nxs(game_domain_name, mod_id, headers=None):
    """Nexus API call.
    
    Returns object of details for provided mod 
    on Nexus if successful, or Exception details.

    Example returned mod data: 
        { "name": str, "summary": str, "description": str of html, 
        "picture_url": str url, "mod_downloads": int, 
        "mod_unique_downloads": int, "uid": int, "mod_id": int, 
        "game_id": int, "allow_rating": bool, "domain_name": str, 
        "category_id": int, "version": str of int, "endorsement_count": int, 
        "created_timestamp": int, "created_time": str of datetime, 
        "updated_timestamp": int, "updated_time": str of datetime, 
        "author": str, "uploaded_by": str, "uploaded_users_profile_url": str url, 
        "contains_adult_content": bool, "status": str, "available": bool, 
        "user": { "member_id": int, "member_group_id": int, "name": str	}, 
        "endorsement": { "endorse_status": str, "timestamp": str of datetime, 
        "version": str of int } }
    """
    
    url = f'{base_url}/v1/games/{game_domain_name}/mods/{mod_id}.json'

    try:
        res = requests.get(url, headers=headers)
        print("RES from API: ", res.json())
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Page: Mod page, Function: get_mod_nxs()\nFailed to retrieve Nexus API data, error: ", e)
        description = 'Mod data could not be retrieved from Nexus.<br>Please ensure requested game domain and mod id are correct and try again.'
        if e.response.status_code == 404:
            abort(404, description)
        elif e.response.status_code == 422:
            abort(422, description)
        else:
            abort(e.response.status_code)
    

    nexus_mod = res.json()

    return nexus_mod


def get_tracked_mods_nxs(headers=None):
    """Nexus API call.
    
    Returns list of objects to identify the mods in the signed-in 
    user's Tracking Centre on Nexus.
    
    Example returned mod data:
    [{'mod_id': int, 'domain_name': str}]
    """
    print(f"headers: {headers}")

    url = f'{base_url}/v1/user/tracked_mods.json'

    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()

    except requests.exceptions.HTTPError as e:
        print("Page: login() or Tracked Mods page\nFunction: get_tracked_mods_nxs()\nFailed to retrieve Nexus API data, error: ", e)
        raise e

    tracked_mods = res.json()
    print("response headers: ", res.headers)

    return tracked_mods


def endorse_mod_nxs(game_domain_name, mod_id, endorse_action, headers=None):
    """Nexus API call.
    
    Sends request to Nexus API to change user's records for the mod 
    with mod_id to 'Endorsed' if unendorsed, or 'Abstained' if endorsed.
    
    API returns HTTP status codes to confirm or refute successful change request.
    Function returns True if successful, or aborts w/ HTTP status code if failed."""

    url = f'{base_url}/v1/games/{game_domain_name}/mods/{mod_id}/{endorse_action}.json'

    try:
        res = requests.post(url, headers=headers)
        res.raise_for_status()

    except requests.exceptions.HTTPError as e:
        print("Page: endorse_mod()\nFunction: endorse_mod_nxs()\nFailed to change user account data on Nexus, error: ", e)
        flash("Sorry, mod endorsement status was not changed.\nAn error was encountered while attempting to have Nexus update your endorsement.\nPlease try again.", 'danger')
        description = 'Mod endorsement could not be updated by Nexus.<br>Please ensure requested game domain and mod id are correct and try again.'
        if e.response.status_code == 400:
            abort(400, description)
        elif e.response.status_code == 403:
            if "NOT_DOWNLOADED_MOD" in res.text:
                description = "Mod endorsement could not be updated by Nexus.\nUsers are not allowed to endorse mods they have not downloaded."
            abort(403, description)
        elif e.response.status_code == 404:
            abort(404, description)
        elif e.response.status_code == 422:
            abort(422, description)
        else:
            abort(e.response.status_code)

    if endorse_action == 'endorse':
        flash("Success! Mod endorsement has been added by your Nexus user account.", 'success')

    if endorse_action == 'abstain':
        flash("Success! Mod endorsement has been removed by your Nexus user account.", 'success')

    return True


def track_mod_nxs(game_domain_name, mod_id, track_action, headers=None):
    """Nexus API call.
    
    Sends request to Nexus API to add to or remove from user's tracked mods list in Nexus' records for the mod with game_domain_name and mod_id.
    
    API returns HTTP status codes to confirm or refute successful change request.
    Function returns True if successful, or aborts w/ HTTP status code if failed."""

    url = f'{base_url}/v1/user/tracked_mods.json?domain_name={game_domain_name}'
    data = {'mod_id':int(mod_id)}

    try:
        if track_action == 'add':
            res = requests.post(url, headers=headers, data=data)
        if track_action == 'delete':
            res = requests.delete(url, headers=headers, data=data)
        res.raise_for_status()

    except requests.exceptions.HTTPError as e:
        print("Page: track_mod()\nFunction: track_mod_nxs()\nFailed to change user account data on Nexus, error: ", e)
        flash("Sorry, mod tracking status was not changed.\nAn error was encountered while attempting to have Nexus update your account's Tracking Centre.\nPlease try again.", 'danger')
        description = 'Mod tracking could not be updated by Nexus.<br>Please ensure requested game domain and mod id are correct and try again.'
        if e.response.status_code == 400:
            abort(400, description)
        elif e.response.status_code == 403:
            abort(403, description)
        elif e.response.status_code == 404:
            abort(404, description)
        elif e.response.status_code == 422:
            abort(422, description)
        else:
            abort(e.response.status_code)

    if track_action == 'add':
        flash("Success! Mod has been added to your Nexus user account's Tracking Centre.", 'success')
    if track_action == 'delete':
        flash("Success! Mod has been removed from your Nexus user account's Tracking Centre.", 'success')

    return True