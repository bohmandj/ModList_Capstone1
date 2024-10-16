import requests
from flask import abort
from flask_sqlalchemy import SQLAlchemy
from secretkeys import nexus_api_key
from app import db
from models import User, Modlist, Mod, Game

base_url = 'https://api.nexusmods.com/'
headers = {'apikey': nexus_api_key}

def get_all_games_nxs(include_unapproved=False):
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

    url = f'{base_url}v1/games.json'

    if include_unapproved:
        url = url.join('?include_unapproved=true')

    res = requests.get(url, params=include_unapproved, headers=headers)
    nexus_games = res.json()

    return nexus_games


def get_mods_of_type_nxs(game, request_type):
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

    url = f'{base_url}v1/games/{game.domain_name}/mods/{request_type}.json'

    try:
        res = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print("Page: Game page, Function: get_mods_of_type_nxs()\nFailed to retrieve Nexus API data, error: ", e)
        return 'error'

    nexus_mods = res.json()

    return nexus_mods


def get_mod_nxs(game_domain_name, mod_id):
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
    
    url = f'{base_url}v1/games/{game_domain_name}/mods/{mod_id}.json'

    try:
        res = requests.get(url, headers=headers)
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


def get_tracked_mods_nxs():
    """Nexus API call.
    
    Returns list of objects to identify the mods in the signed-in 
    user's Tracking Centre on Nexus.
    
    Example returned mod data:
    [{'mod_id': int, 'domain_name': str}]
    """

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