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

    Optionally can also include unapproved games. ( include_unapproved=True )"""

    url = f'{base_url}v1/games.json'

    if include_unapproved:
        url = url.join('?include_unapproved=true')

    try:
        res = requests.get(url, params=include_unapproved, headers=headers)
        nexus_games = res.json()

    except Exception as e:
        print("Failed to retrieve API data", res.status_code)
        print("Error: ", e)
        return e

    return nexus_games
            

         