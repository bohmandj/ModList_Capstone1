import requests
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

    try:
        res = requests.get(url, params=include_unapproved, headers=headers)

    except requests.exceptions.RequestException as e:
        print("get_all_games_nxs() Failed to retrieve API data: ", res.status_code)
        print("Error: ", e)
        raise

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
        print(f'NEXUS API RESPONSE: ', res)

    except requests.exceptions.RequestException as e:
        print("get_mods_of_type_nxs() Failed to retrieve API data: ", res.status_code)
        print("Error: ", e)
        raise

    nexus_mods = res.json()

    return nexus_mods