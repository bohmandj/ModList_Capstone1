import os

from flask import Flask, render_template, request, flash, redirect, session, g, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, UserEditForm
from models import db, connect_db, User, Modlist, Mod, Game

from nexus_api import get_all_games_nxs, get_mods_of_type_nxs
from utilities import get_all_games_db, filter_nxs_data, update_all_games_db, get_game_db

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///modlist_db'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)
with app.app_context():
    db.create_all()


##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user.
    
    Returns Exception if error occurs during Nexus API call
    or db update."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    
    if 'csrf_token' in session:
        del session['csrf_token']


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, re-present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")

            # use updated list of games on Nexus from API to update db
            try:
                nexus_games = get_all_games_nxs()
                print(nexus_games[0])
                db_ready_games = filter_nxs_data(nexus_games, 'game')
                print(db_ready_games)
                tf = update_all_games_db(db_ready_games)
                print(tf)
            except:
                flash("Problem occurred refreshing games list from Nexus.\nDisplayed games list may be out of date or incomplete.\nLog out and back in to reattempt.", "danger")

            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    if not g.user:
        flash("You must sign in before you can sign out.", "danger")

        return redirect("/login")

    do_logout()
    flash(f"Logout successful!", "success")

    return redirect("/login")


##############################################################################
# User routes:


##############################################################################
# Game routes (& Mod routes):

@app.route('/games/<game_domain_name>')
def show_game_page(game_domain_name):
    """Show game page with mods hosted by Nexus.
    
    - Nexus API is called to populate Mod categories on page.
    -- Mod Categories: Trending, Latest Added, Latest Updated.
    - Buttons linking to game page on Nexus for further browsing.
    """

    try:
        game = get_game_db(game_domain_name)
        print(f'############### s_g_p route, game return: {game} ###############')
    except:
        flash("Issue was encountered retrieving game information.")
        return redirect(url_for('homepage'))

    mod_categories = [
        {'mod_cat': 'trending', 'section_title':'Trending Mods'}, 
        {'mod_cat': 'latest_added', 'section_title':'Latest Added Mods'}, 
        {'mod_cat': 'latest_updated', 'section_title':'Latest Updated Mods'}
    ]

    for cat in mod_categories:
        try:
            print("GAME // ", game, " //")
            nxs_category = get_mods_of_type_nxs(game, cat['mod_cat'])
        except Exception as e:
            cat['error'] = True
            print(f'CAT ERROR: {e}')
            raise
        else:
            db_ready_data = filter_nxs_data(nxs_category, 'mod', game_obj=game)
            cat['data'] = db_ready_data

    return render_template('games/game.html', game=game, mod_categories=mod_categories)


@app.route('/games/<game_domain_name>/mods/<mod_id>')
def show_mod_page(game_domain_name, mod_id):
    """Show mod page of info about a mod hosted on Nexus.
    
    - Nexus API is called to populate details about the mod.
    - Details include: title, image, author, last update date, 
    summary, full description.
    - Buttons to: track/untrack and endorse/un-endorse on Nexus.
    - Lists of known conflicts, known required mods, 
    and ability to update those lists.
    - Button to add mod to one of your ModLists.
    - Link to official mod page on Nexus.
    """

    return render_template('games/mod.html', game=game)


##############################################################################
# Homepage and error pages

@app.route('/')
def homepage():
    """Show homepage:

    - anon users: sign up pitch page 
      (must also be signed in to Nexus SSO for API to function)

    - logged in: show list of popular games Nexus hosts mods for 
    """ 
    # maybe also links to common locations?
    # stretch: alphabetical list of all games Nexus hosts mods for searchable by letter

    if g.user:       
        try:
            games_list = get_all_games_db()
        except Exception as e:
            print("Error getting games from db: ", e)
            flash("Problem occurred fetching games list, log out and back in to reattempt.")
        else:
            return render_template('home.html', games_list=games_list)

        return render_template('home.html', games_list=[{'name':"Error"}])

    return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production handled elsewhere)
@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req