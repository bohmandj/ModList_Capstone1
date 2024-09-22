import os

from flask import Flask, render_template, request, flash, redirect, session, g, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, UserEditForm, ModlistAddForm
from models import db, connect_db, User, Modlist, Mod, Game

from nexus_api import get_all_games_nxs, get_mods_of_type_nxs, get_mod_nxs
from utilities import get_all_games_db, get_game_db, get_mod_db, filter_nxs_data, filter_nxs_mod_page, update_all_games_db, update_list_mods_db, link_mods_to_game

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

        Modlist.new_modlist(
            name='Nexus Tracked Mods', 
            description="This ModList automatically populates with all the mods in your Nexus account's Tracking centre. Use the Tracking feature on Nexus to easily bring mods over to ModList while browsing on Nexus. Mark mods 'keep tracked' in this ModList to make sure you don't accidentally un-track something you actually want tracked on Nexus for update notifications. From here you can you can also add mods to your other ModLists, or un-track mods you don't want to keep tracked on Nexus.", 
            user=user
        )

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

                db_ready_games = filter_nxs_data(nexus_games, 'games')

                update_all_games_db(db_ready_games)
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
# User routes (& ModList routes):

@app.route('/users/<user_id>')
def show_user_page(user_id):
    """Show user profile page.
    
    - Display games for which user has lists with small
      selection of their lists.
    - Buttons to: go to list, go to game, make new list.
    """

    user = User.query.get_or_404(user_id)
    modlists = user.modlists
    # print("MODLISTS:::::::::: ", modlists[0])
    # games = user.get_users_games()
    # print("games:::::::::: ", games)

    games = []
    # for game in user.get_users_games():
    #     modlists = user.get_recent_modlists(modlists)
    #     games.append({'game':game, 'modlists':modlists})
    if len(games) == 0:
        games = ['Empty']
    if len(modlists) == 0:
        modlists = ['Empty']
    return render_template('users/profile.html', user=user, games=games, modlists=modlists)


@app.route('/users/edit', methods=["GET", "POST"])
def edit_profile():
    """Update profile info for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserEditForm()

    if form.validate_on_submit():
        user = User.authenticate(g.user.username, form.current_password.data)
        if user == False:
            flash("Username and/or password did not match our records. Please try again.", 'danger')
            return render_template('users/edit.html', form=form)

        try:
            g.user.username = form.username.data
            db.session.commit()
        except:
            db.session.rollback()
            flash("Username already taken", 'danger')
            return render_template('users/edit.html', form=form)
        
        try:
            g.user.email = form.email.data
            db.session.commit()
        except:
            db.session.rollback()
            flash("Email already taken. Every email can only be associated with a single account.", 'danger')
            return render_template('users/edit.html', form=form)

        g.user.hide_nsfw = form.hide_nsfw.data

        db.session.commit()

        return redirect(f'/users/{g.user.id}')

    # pre-fill forms w/ user data
    form.username.data = g.user.username
    form.email.data = g.user.email
    form.hide_nsfw.data = g.user.hide_nsfw

    return render_template('users/edit.html', form=form)


@app.route('/users/<user_id>/modlists/new', methods=["GET", "POST"])
def new_modlist(user_id):
    """Handle new ModList generation.

    Create new ModList and add to DB. Redirect to new ModList page.

    If form not valid, re-present form.

    If the there already is a ModList with that name owned by the 
    same user: flash message and re-present form.
    """

    form = ModlistAddForm()

    if form.validate_on_submit():
        try:
            modlist = Modlist.new_modlist(
                name=form.name.data,
                description=form.description.data,
                private=form.private.data,
                user=g.user
            )
            db.session.commit()

        except Exception as e:
            print("Error creating Modlist: ", e)
            flash("Error creating ModList, please try again.", 'danger')
            return render_template('users/modlist-new.html', form=form)

        return redirect(url_for("show_user_page", user_id=g.user.id))

    else:
        return render_template('users/modlist-new.html', form=form)


@app.route('/users/<user_id>/modlists/<modlist_id>')
def show_modlist_page(user_id, modlist_id):
    """Show modlist page.

    - db is searched for contents of the ModList.
    - Buttons: link to each mod page, remove mod from list, 
    """


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
        # return redirect(url_for('homepage'))
        raise

    mod_categories = [
        {'mod_cat': 'trending', 'section_title':'Trending Mods'}, 
        {'mod_cat': 'latest_added', 'section_title':'Latest Added Mods'}, 
        {'mod_cat': 'latest_updated', 'section_title':'Latest Updated Mods'}
    ]

    for cat in mod_categories:
        print(f""":::::::::::::::::::PRE-NEXUS API CALL:::::::::::::::::::: {cat['section_title']}""")
        try:
            print("GAME // ", game, " //")
            nxs_category = get_mods_of_type_nxs(game, cat['mod_cat'])
        except Exception as e:
            cat['error'] = True
            print(f'CAT ERROR: {e}')
            raise
        else:
            db_ready_data = filter_nxs_data(nxs_category, 'mods')
            cat['data'] = db_ready_data
            update_list_mods_db(db_ready_data, game)
            link_mods_to_game(db_ready_data, game)

    if not g.user:
        hide_nsfw = True
    else:
        hide_nsfw = g.user.hide_nsfw

    return render_template('games/game.html', game=game, mod_categories=mod_categories, hide_nsfw=hide_nsfw)


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
   
    try:
        game = get_game_db(game_domain_name)
        print(f'############### s_m_p route, get_game_db() return: {game} ###############')
    except:
        flash("Issue was encountered retrieving game information.")
        # return redirect(url_for('homepage'))
        raise

    ### Pull relevant data out of API response object to populate page, render_template for mod page ###
    nexus_mod = get_mod_nxs(game, mod_id)

    db_ready_mods = filter_nxs_data([nexus_mod], 'mods')
    update_list_mods_db(db_ready_mods, game)
    link_mods_to_game(db_ready_mods, game)

    print("Subject of Mods::::::: ", game.subject_of_mods)

    page_ready_mod = filter_nxs_mod_page(nexus_mod, game)

    if not g.user:
        hide_nsfw = True
    else:
        hide_nsfw = g.user.hide_nsfw

    return render_template('games/mod.html', game=game, mod=page_ready_mod, hide_nsfw=hide_nsfw)


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