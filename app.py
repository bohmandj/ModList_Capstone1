import os

from flask import Flask, render_template, request, flash, redirect, session, g, url_for, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from functools import wraps
from werkzeug.datastructures import ImmutableDict
from urllib.parse import urlparse
from flask_wtf.csrf import CSRFProtect
from cryptography.fernet import Fernet
import requests

from forms import RegisterForm, LoginForm, UserEditForm, UserPasswordForm, ModlistAddForm, ModlistEditForm, ModlistAddModForm
from models import db, connect_db, User, Modlist, Mod, Game

from nexus_api import get_all_games_nxs, get_mods_of_type_nxs, get_mod_nxs, endorse_mod_nxs, track_mod_nxs
from utilities import get_all_games_db, get_game_db, get_empty_modlists, get_tracked_modlist_db, get_recent_modlists_by_game, get_public_modlists_by_game, filter_nxs_data, filter_nxs_mod_page, update_all_games_db, update_list_mods_db, link_mods_to_game, add_mod_modlist_choices, flash_modlist_action_messages, check_modlist_uneditable, update_tracked_mods_from_nexus, get_tracked_not_keep_db, paginate_tracked_mods, paginate_modlist_mods

CURR_USER_KEY = "curr_user"
ORDER = "update"
PER_PAGE = "25"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///modlist_db'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
app.config['WTF_CSRF_ENABLED'] = True
csrf = CSRFProtect(app)
toolbar = DebugToolbarExtension(app)

connect_db(app)
with app.app_context():
    db.create_all()

encryption_key = os.environ.get('FERNET_ENCRYPTION_KEY')
if encryption_key is None:
    raise RuntimeError("Encryption key not found in environment variables")
cipher_suite = Fernet(encryption_key)

##############################################################################
# Custom decorators

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.user:
            flash("Access unauthorized.", "danger")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def set_listview_query_vals(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        page = request.args.get('page', default=1, type=int)
        req_per_page = request.args.get('per_page', default=25, type=int)
        req_order = request.args.get('order', default='update', type=str)

        if 'set_per_page' in request.args:
            session[PER_PAGE] = request.args['set_per_page']
            page = 1
        per_page = session[PER_PAGE] if PER_PAGE in session else int(req_per_page)

        if 'set_order' in request.args:
            session[ORDER] = request.args['set_order']
            page = 1
        order = session[ORDER] if ORDER in session else req_order

        if 'page_reset' in kwargs:
            page = 1
        
        return f(*args, **kwargs, page=int(page), per_page=int(per_page), order=order)
    return decorated_function

def get_api_headers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        encrypted_api_key = session.get('user_api_key')
        if not encrypted_api_key:
            flash("Nexus API key not found. Please login and enter your Nexus account's personal API key. API key is not saved to our server, so it must be entered every time you log in to ModList. If logged in to Nexus, the key can be found at the bottom of this page: https://next.nexusmods.com/settings/api-keys", "danger")
            do_logout()
            return redirect(url_for('login', next=request.url))
        user_api_key = cipher_suite.decrypt(encrypted_api_key).decode()
        headers = {'apikey': user_api_key}
        return f(*args, **kwargs, headers=headers)
    return decorated_function


##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = db.session.execute(
            db.select(User)
            .where(User.id==session[CURR_USER_KEY])
            ).scalars().first()
    else:
        g.user = None


def do_login(user):
    """Log in user.
    
    Returns Exception if error occurs during Nexus API call
    or db update."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    session.clear()

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

    if g.user:
        return redirect(url_for('homepage'))

    form = RegisterForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data
            )
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if e.__cause__.diag.constraint_name == "users_username_key":
                flash("Username already taken", 'danger')
            if e.__cause__.diag.constraint_name == "users_email_key":
                flash("Email already used - each email can only be used on one account", 'danger')
            return render_template('users/signup.html', form=form)

        modlist = Modlist.new_modlist(
            name='Nexus Tracked Mods', 
            description="This modlist automatically populates with all the mods in your Nexus account's Tracking Centre.", 
            private=True,
            user=user
        )
        db.session.add(modlist)
        db.session.commit()

        return redirect(url_for('login'))

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    if g.user:
        return redirect(url_for('homepage'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)

            user_api_key = form.user_api_key.data
            encrypted_api_key = cipher_suite.encrypt(user_api_key.encode())
            session['user_api_key'] = encrypted_api_key
            headers = {'apikey': user_api_key}

            flash(f"Hello, {user.username}! Welcome back.", "success")

            # use list of all games from Nexus API to update all Games in db
            try:
                nexus_games = get_all_games_nxs(headers=headers)
                db_ready_games = filter_nxs_data(nexus_games, 'games')
                update_all_games_db(db_ready_games)
            except:
                flash("Problem occurred refreshing games list from Nexus.\nDisplayed games list may be out of date or incomplete.\nLog out and back in to reattempt.", "danger")

            # use mods from Nexus Tracking Centre to update user's Nexus Tracked Mods modlist
            tracked_mod_ids = update_tracked_mods_from_nexus(user.id, headers=headers)
            session['tracked_mod_ids'] = tracked_mod_ids

            next_page = request.form.get('next')

            if next_page:
                parsed_url = urlparse(next_page)
                if parsed_url.netloc == '' or parsed_url.scheme in ['http', 'https']:
                    return redirect(next_page or url_for('homepage'))
            return redirect(url_for('homepage'))

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Handle logout of user."""

    do_logout()
    flash(f"Logout successful!", "success")

    return redirect(url_for('login'))


##############################################################################
# Tracked Mods Modlist routes:


@app.route('/users/modlists/<string:tab>')
@login_required
@set_listview_query_vals
@get_api_headers
def show_tracked_modlist_page(tab='tracked-mods', page=1, per_page=25, order="update", headers=None, **kwargs):
    """Show the regular 'Tracked' side of the user's 
    'Nexus Tracked Mods' modlist page. These mods are imported 
    from Nexus, but are not marked with the 'Keep Tracked' tag 
    to separate them from the rest of the imported mods.

    Variable 'tab' determines if tracked mods (not marked keep-tracked), 
    keep-tracked mods will be displayed, OR if user's tracked mods data 
    will get synced with Nexus' records. Only 'tracked-mods', 
    'keep-tracked-mods', or 'tracked-sync' are valid inputs.
    Mod display order takes 'order' arguments from the query string - 'author' or 'name' valid, otherwise mods display most recently updated first.
    Pagination takes 'page' and 'per_page' arguments from the query string.
    """
    print(f"headers 361: {headers}")

    if tab == 'tracked-sync':
        tracked_mod_ids = update_tracked_mods_from_nexus(g.user.id, headers=headers)
        session['tracked_mod_ids'] = tracked_mod_ids
        return redirect(url_for('show_tracked_modlist_page', tab='tracked-mods'))

    page_mods = paginate_tracked_mods(g.user.id, page, per_page, order=order, tab=tab)

    tracked_modlist = get_tracked_modlist_db(g.user.id)

    return render_template("users/modlist-tracked.html", page_mods=page_mods, page=page, per_page=per_page, order=order, tab=tab, modlist=tracked_modlist)


@app.route('/users/modlists/keep-tracked-mods/mods/<int:mod_id>/<string:keep_action>', methods=["POST"])
@login_required
def change_keep_tracked_status(mod_id, keep_action):
    """Add/delete tracked mod to/from keep-tracked tab of user's 
    Nexus Tracked Mods modlist.

    - db is searched for mod and user.
    - If mod is not in user.keep_tracked, add to keep-tracked list.
    - If mod is in user_keep_tracked, remove from keep-tracked list.
    """

    next_page = request.args.get('next')

    user = db.session.execute(
        db.select(User)
        .options(db.selectinload(User.keep_tracked))
        .where(User.id == g.user.id)
    ).scalars().first()
    
    mod = db.session.execute(
        db.select(Mod)
        .where(Mod.id == mod_id)
    ).scalars().first()

    if not mod:
        description = f"A mod with ID #{mod_id} could not be found.<br>We either encountered an issue retrieving the data from our database, or the mod does not exist.<br>Please check that the correct mod id is being requested and try again."
        abort(404, description)

    if keep_action == 'add':
        if mod not in user.keep_tracked:
            try:
                user.keep_tracked.append(mod)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print("Page: add_keep_tracked_mod route, Function: user.keep_tracked.append(mod) + commit\nFailed to add mod to keep_tracked, error: ", e)
                description = f"Sorry, an error was encountered and and '{mod.name}' was not added to your Keep Tracked list. Please try again."
                abort(500, description)
            else:
                flash(f"Success! '{mod.name}' has been added to your Keep-Tracked list.", 'success')
        else:
            flash(f"'{mod.name}' could not be added because it is already in your Keep Tracked list.", 'danger')
        
    elif keep_action == 'delete':
        if mod in user.keep_tracked:
            try:
                user.keep_tracked.remove(mod)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print("Page: add_keep_tracked_mod route, Function: user.keep_tracked.remove(mod) + commit\nFailed to delete mod from keep_tracked, error: ", e)
                description = f"Sorry, an error was encountered and and '{mod.name}' was not removed from your Keep Tracked list. Please try again."
                abort(500, description)
            else:
                flash(f"Success! '{mod.name}' has been removed from your Keep-Tracked list.", 'success')
        else:
            flash(f"'{mod.name}' could not be removed because it is not in your Keep Tracked list.", 'danger')

    else:
        description = f"The action '{keep_action}' in the requested url is not valid. Please use 'add' or 'delete' to change whether or not a mod is in the Keep-Tracked tab of your Nexus Tracked Mods modlist."
        abort(400, description)

    if next_page:
        parsed_url = urlparse(next_page)
        if parsed_url.netloc == '' or parsed_url.scheme in ['http', 'https']:
            return redirect(next_page or url_for('show_tracked_modlist_page', tab='tracked-mods'))
    return redirect(url_for('show_tracked_modlist_page', tab='tracked-mods'))


##############################################################################
# Users-made Modlist routes:


@app.route('/users/<int:user_id>/modlists/<int:modlist_id>')
@set_listview_query_vals
def show_modlist_page(user_id, modlist_id, page=1, per_page=25, order="update"):
    """Show the user's modlist page. 

    Mod display order takes 'order' arguments from the query string - 'author' or 'name' valid, otherwise mods display most recently updated first.
    Pagination takes 'page' and 'per_page' arguments from the query string.
    """
    print("SHOW_MODLIST_PAGE STARTED")
    modlist = db.get_or_404(Modlist, modlist_id, description=f"Sorry, we couldn't find modlist #{modlist_id}.<br>We either encountered an issue retrieving the data from our database, or the modlist does not exist.<br>Please try again or use a different modlist.")

    user = db.get_or_404(User, user_id, description=f"Sorry, we couldn't find user #{user_id}.<br>We either encountered an issue retrieving the data from our database, or the user does not exist.<br>Please try again or use a different user.")

    if int(modlist.user_id) != int(user_id):
        description = 'Make sure User ID and Modlist ID are compatible.<br>The  requested modlist must be owned by the requested user.'
        abort(404, description)

    page_mods = paginate_modlist_mods(user_id, modlist_id, page, per_page, order)

    if not g.user:
        hide_nsfw = True
    else:
        hide_nsfw = g.user.hide_nsfw
    
    print("SHOW_MODLIST_PAGE About to return users/modlist.html")
    return render_template('users/modlist.html', page_mods=page_mods, page=page, per_page=per_page, order=order, user=user, modlist=modlist, hide_nsfw=hide_nsfw)


@app.route('/users/modlists/<int:modlist_id>/mods/<int:mod_id>/delete', methods=["POST"])
@login_required
def modlist_delete_mod(modlist_id, mod_id):
    """Remove mod from modlist.

    - db is searched for mod and modlist.
    - if mod is found in list of mods contained in modlist, 
      delete mod from modlist.
    """

    modlist = db.get_or_404(Modlist, modlist_id, description=f"Sorry, we couldn't find a modlist with ID #{modlist_id}.<br>We either encountered an issue retrieving the data from our database, or the modlist does not exist.<br>Please check that the correct modlist id is being requested and try again.")

    is_invalid = check_modlist_uneditable(modlist, g.user.id)
    if is_invalid:
        flash(is_invalid, "danger")
        return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    else:
        mod = db.get_or_404(Mod, mod_id, description=f"Sorry, we couldn't find a mod with ID #{mod_id}.<br>We either encountered an issue retrieving the data from our database, or the mod does not exist.<br>Please check that the correct mod id is being requested and try again.")
        try:
            if mod in modlist.mods:
                modlist.mods.remove(mod)
            else:
                flash(f"Can't delete mod from modlist. {mod.name} not found in {modlist.name}.", 'danger')
                return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print("Error deleting mod from modlist in db - modlist_delete_mod(): ", e)
            flash(f"Error removing {mod.name} from {modlist.name}, please try again.", 'danger')
            return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    flash(f'{mod.name} successfully removed from {modlist.name}!', 'success')
    print(f"modlist.mods: {modlist.mods}")
    print(f"len(modlist.mods): {len(modlist.mods)}")
    if len(modlist.mods) <= 0:
        for game in modlist.for_games:
            try:
                print(f"modlist.for_games: {modlist.for_games}")
                modlist.for_games.remove(game)
                db.session.commit()
            except Exception as e:
                print("Page: modlist_delete_mod, Function: modlist.for_games.remove(game)\nFailed to un-assign modlist's game assignment, error: ", e)
                abort(500, f"Only mod was removed from modlist, but an error was encountered removing modlist's assignment to {game.name}.<br>Modlist will still only take mods for {game.name}.<br>Options to resolve future issues with this modlist are:<br>1. Add and remove a mod to reattempt game assignment removal<br>2. Delete this modlist and make a new one.")

    return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    
@app.route('/users/modlists/<int:modlist_id>/edit', methods=["GET", "POST"])
@login_required
def edit_modlist(modlist_id):
    """Update modlist info for modlist belonging to current user."""

    form = ModlistEditForm()

    modlist = db.get_or_404(Modlist, modlist_id, description=f"Sorry, we couldn't find a modlist with ID #{modlist_id}.<br>We either encountered an issue retrieving the data from our database, or the modlist does not exist.<br>Please check that the correct modlist id is being requested and try again.")

    is_invalid = check_modlist_uneditable(modlist, g.user.id)
    if is_invalid:
        flash(is_invalid, "danger")
        return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    if form.validate_on_submit():

        users_modlists = db.session.scalars(db.select(Modlist).where(Modlist.user_id==g.user.id).order_by(Modlist.name)).all()

        users_modlist_names = ['Nexus Tracked Mods']

        for mlist in users_modlists:
            if mlist.id != int(modlist_id):
                users_modlist_names.append(mlist.name)
            else:
                modlist = mlist
        
        try:
            if form.name.data in users_modlist_names:
                raise ValueError("Modlist name can not be used twice by same user.")

            modlist.name=form.name.data
            modlist.description=form.description.data,
            modlist.private=form.private.data

            db.session.commit()

        except ValueError as e:
            db.session.rollback()
            flash(f"You already have a modlist named '{form.name.data}', please choose another name.", 'danger')
            return redirect(url_for('edit_modlist', modlist_id=modlist_id))
        
        except Exception as e:
            db.session.rollback()
            print("Error saving modlist edits to db: ", e)
            flash("Sorry, there was a problem saving your edited modlist. Please try again.", 'danger')
            return redirect(url_for('edit_modlist', modlist_id=modlist_id))

        flash(f"Success! Edits to '{modlist.name}' saved.", 'success')

        return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    # pre-fill forms w/ modlist data
    form.name.data=modlist.name
    form.description.data=modlist.description
    form.private.data=modlist.private

    return render_template('users/edit.html', form=form, form_title="Edit Modlist", modlist=modlist)

    
@app.route('/users/modlists/<int:modlist_id>/delete', methods=["POST"])
@login_required
def delete_modlist(modlist_id):
    """Delete user's modlist.

    - db is searched for user and modlist.
    - if modlist is found in list of user's modlists, 
      delete modlist.
    """

    modlist = db.get_or_404(Modlist, modlist_id, description=f"Sorry, we couldn't find a modlist with ID #{modlist_id}.<br>We either encountered an issue retrieving the data from our database, or the modlist does not exist.<br>Please check that the correct modlist id is being requested and try again.")

    is_invalid = check_modlist_uneditable(modlist, g.user.id)
    if is_invalid:
        flash(is_invalid, "danger")
        return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    user = db.session.execute(
        db.select(User)
        .options(db.selectinload(User.modlists))
        .where(User.id == g.user.id)
    ).scalars().first()
    try:
        # Remove all mods related to this modlist from modlist_mod table
        if modlist.mods:
            modlist.mods.clear()
        # Delete the modlist itself
        db.session.delete(modlist)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Error deleting modlist from db - delete_modlist(): ", e)
        flash(f"An error occurred and modlist '{modlist.name}' was not deleted.\nPlease try again.", 'danger')
        return redirect(url_for('show_modlist_page', user_id=modlist.user_id, modlist_id=modlist_id))

    flash(f"Success! Modlist '{modlist.name}' has been deleted!", 'success')
    return redirect(url_for("show_user_page", user_id=g.user.id))


@app.route('/users/modlists/add/mods/<int:mod_id>', methods=["GET", "POST"])
@login_required
def modlist_add_mod(mod_id):
    """Add mod to modlist.

    - Database is searched for mod and user's modlists.
    - If mod not in list of mods contained in selected modlists, 
      add mod to modlist.
    """

    form = ModlistAddModForm()

    mod = db.get_or_404(Mod, mod_id, description=f"Sorry, we couldn't find a mod with ID #{mod_id}.<br>We either encountered an issue retrieving the data from our database, or the mod does not exist.<br>Please check that the correct mod id is being requested and try again.")

    if form.validate_on_submit():

        modlist_ids = form.users_modlists.data


        unowned_modlists = []
        already_in_modlists = []
        successfully_added = []
        encountered_error = []

        modlists = db.session.scalars(db.select(Modlist).where(Modlist.id.in_(modlist_ids))).all()
        for modlist in modlists:
            
            if modlist.user_id != g.user.id:
                unowned_modlists.append(f"'{modlist.name}'")
                continue

            if mod in modlist.mods:
                already_in_modlists.append(f"'{modlist.name}'")
                continue

            try:
                modlist.mods.append(mod)
                modlist.mark_nsfw_if_nsfw(mod)
                for game in mod.for_games:
                    game = db.get_or_404(Game, game.id, description=f"Sorry, we couldn't find a game with ID #{game.id}.<br>We either encountered an issue retrieving the data from our database, or the game does not exist.<br>Please check that the correct game id is being requested and try again.")
                    modlist.assign_modlist_for_games(game)
                modlist.update_mlist_tstamp()

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                print(f"Error adding mod to modlist in db - modlist_add_mod():  {e}\nError context: mod.name: {mod.name}; modlist.name: {modlist.name}")
                encountered_error.append(f"'{modlist.name}'")
            
            successfully_added.append(modlist.name)

        flash_modlist_action_messages(mod.name, successfully_added, unowned_modlists, already_in_modlists, encountered_error)

        return redirect(url_for('show_mod_page', game_domain_name=mod.for_games[0].domain_name, mod_id=mod_id))

    
    # pre-fill form w/ available data
    choices_response = add_mod_modlist_choices(g.user.id, mod)
    users_modlist_choices = choices_response['users_modlist_choices']
    users_empty_modlist_choices = choices_response['users_empty_modlist_choices']
    no_modlists = True if users_modlist_choices + users_empty_modlist_choices == [] else False
    modlists_w_mod = choices_response['modlists_w_mod']
    form_choices = [(modlist.id, f"{modlist.name} (Empty)") for modlist in users_empty_modlist_choices]
    form_choices = form_choices + [(modlist.id, modlist.name) for modlist in users_modlist_choices]
    form.users_modlists.choices = form_choices

    return render_template('users/modlist-add.html', form=form, user=g.user, mod=mod, modlists_w_mod=modlists_w_mod, no_modlists=no_modlists)


@app.route('/users/modlists/new', methods=["GET", "POST"])
@login_required
def new_modlist():
    """Handle new modlist generation.

    Create new modlist and add to DB. Redirect to new modlist page.

    If form not valid, re-present form.
    """

    form = ModlistAddForm()

    if form.validate_on_submit():
        next_page = request.args.get('next')

        try:
            current_modlists = db.session.scalars(db.select(Modlist).where(Modlist.user_id==g.user.id).order_by(Modlist.name)).all()

            if form.name.data in [modlist.name for modlist in current_modlists]:
                raise ValueError(f"You already have a modlist named '{form.name.data}', please choose another name.")

            modlist = Modlist.new_modlist(
                name=form.name.data,
                description=form.description.data,
                private=form.private.data,
                user=g.user
            )
            db.session.add(modlist)
            db.session.commit()

        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return render_template('users/modlist-new.html', form=form, next=next_page)

        except Exception as e:
            db.session.rollback()
            print("Error creating modlist: ", e)
            flash("Modlist was not created due to an error, please try again.", 'danger')
            return render_template('users/modlist-new.html', form=form, next=next_page)

        if next_page:
            parsed_url = urlparse(next_page)
            if parsed_url.netloc == '' or parsed_url.scheme in ['http', 'https']:
                return redirect(next_page or url_for("show_user_page", user_id=g.user.id))
        return redirect(url_for("show_user_page", user_id=g.user.id))

    return render_template('users/modlist-new.html', form=form)


##############################################################################
# User routes:

@app.route('/users/<int:user_id>')
def show_user_page(user_id):
    """Show user profile page.
    
    - Display games for which user has lists with small
      selection of their lists.
    - Buttons to: go to list, go to game, make new list.
    """

    user = db.get_or_404(User, user_id, description=f"Sorry, we couldn't find a user with ID #{user_id}.<br>We either encountered an issue retrieving the data from our database, or the user does not exist.<br>Please check that the correct user id is being requested and try again.")

    if not g.user or g.user.id != int(user_id):

        modlists_by_game = get_public_modlists_by_game(user_id)

        return render_template('users/profile-public.html', user=user, modlists_by_game=modlists_by_game)
        
    empty_modlists = get_empty_modlists(g.user.id)
    modlists_by_game = get_recent_modlists_by_game(g.user.id)


    return render_template('users/profile-user.html', user=user, empty_modlists=empty_modlists, modlists_by_game=modlists_by_game)


@app.route('/users/edit', methods=["GET", "POST"])
@login_required
def edit_profile():
    """Update profile info for current user."""

    form = UserEditForm()

    if form.validate_on_submit():

        user = User.authenticate(g.user.username, form.current_password.data)
        if user == False:
            flash("Password did not match our records for the currently signed-in user account. Please try again.", 'danger')
            return redirect(url_for('edit_profile'))

        try:
            g.user.username = form.username.data
            g.user.email = form.email.data
            g.user.hide_nsfw = form.hide_nsfw.data
            db.session.commit()
        
        except IntegrityError as e:
            db.session.rollback()
            if e.__cause__.diag.constraint_name == "users_username_key":
                flash("Username already taken, please try again with a different username.", 'danger')
            if e.__cause__.diag.constraint_name == "users_email_key":
                flash("Email already used - each email can only be used on one account", 'danger')
            return redirect(url_for('edit_profile'))

        flash(f"Success! Edits to {form.username.data} saved.", 'success')

        return redirect(url_for('show_user_page', user_id=g.user.id))

    # pre-fill forms w/ user data
    form.username.data = g.user.username
    form.email.data = g.user.email
    form.hide_nsfw.data = g.user.hide_nsfw

    return render_template('users/edit.html', form=form, user=g.user)


@app.route('/users/password', methods=["GET", "POST"])
@login_required
def edit_password():
    """Update password for current user."""

    form = UserPasswordForm()

    if form.validate_on_submit():

        user = User.authenticate(g.user.username, form.current_password.data)

        if user == False:
            flash("Password did not match our records for the currently signed-in user account. Please try again.", 'danger')
            return render_template('users/password.html', form=form, user=g.user)

        if form.new_password.data != form.new_confirm.data:
            flash("New password and confirmation password did not match. Please try again.", 'danger')
            return render_template('users/password.html', form=form, user=g.user)

        try:
            hashed_password = user.hash_new_password(form.new_password.data)
            user.password = hashed_password
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Page: edit_password\nFunction: hash_new_password()\n;Error making/committing new hashed password to db, error: ", e)
            flash("Error saving new password. Please try again.", 'danger')
            return render_template('users/password.html', form=form, user=g.user)

        flash("Success! New password saved.", 'success')

        return redirect(url_for('show_user_page', user_id=g.user.id))

    return render_template('users/password.html', form=form, user=g.user)


@app.route('/users/delete', methods=["POST"])
@login_required
def delete_user():
    """Delete user's account.

    - User is searched for in, and deleted from, the db.
    """

    user = db.get_or_404(User, g.user.id, description=f"Sorry, we encountered an issue retrieving user data from our database. User account has not been deleted.<br>Please try again.")
    username = user.username

    try:
        # Delete user and let db delete cascades clear user's assets
        db.session.delete(user)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print("Error deleting user from db - delete_user(): \n", e, "\nAttempting asset deletion before user deletion.")

        try:
            # Clear all assets associated with the user from the db
            for modlist in user.modlists:
                modlist.mods.clear()
                modlist.for_games.clear()
                db.session.delete(modlist)
            # Finally, delete the user
            db.session.delete(user)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print("Error in asset deletion before user deletion - delete_user(): \n", e)
            flash("An error occurred and your user account was not deleted. Please try again.", "danger")
            return redirect(url_for('show_user_page', user_id=g.user.id))

    do_logout()
    flash(f"Success! User account '{username}' has been deleted!", 'success')

    return redirect(url_for("homepage"))


##############################################################################
# Game routes (& Mod routes):


@app.route('/games/<string:game_domain_name>/mods/<int:mod_id>')
@login_required
@get_api_headers
def show_mod_page(game_domain_name, mod_id, headers=None):
    """Show mod page of info about a mod hosted on Nexus.
    
    - Nexus API is called to populate details about the mod.
    - Details include: title, image, author, last update date, 
    summary, full description.
    - Buttons to: track/untrack and endorse/un-endorse on Nexus.
    - Lists of known conflicts, known required mods, 
    and ability to update those lists.
    - Button to add mod to one of your modlists.
    - Link to official mod page on Nexus.
    """
    
    nexus_mod = get_mod_nxs(game_domain_name, mod_id, headers=headers)
    tracked_mod_ids = None

    try:
        # update mod in db from relevant data in API response object
        game = get_game_db(game_domain_name)
        if not game:
            raise AttributeError(f"No Game object returned from get_game_db(). Game could not be found using '{game_domain_name}'")
        db_ready_mods = filter_nxs_data([nexus_mod], 'mods')
        update_list_mods_db(db_ready_mods)
        link_mods_to_game(db_ready_mods, game)
        db.session.commit()
    except Exception as e:
        # above try block not necessary for page display, continue to display page
        db.session.rollback()
        print("Page: Mod page, Function: get_game_db() or,\n____filter_nxs_data() or,\n____update_list_mods_db() or,\n____link_mods_to_game()\nFailed to update mod in db from Nexus API response; error: ", e)   

    # Pull relevant data out of API response object to populate page
    page_ready_mod = filter_nxs_mod_page(nexus_mod)
    if str(mod_id) in session:
        if session[str(mod_id)] != page_ready_mod['user_endorsed']:
            page_ready_mod['user_endorsed'] = "Not-Updated"
        else:
            del session[str(mod_id)]

    if not page_ready_mod:
        description = 'Mod data could not be retrieved from Nexus.<br>Please ensure requested game domain and mod id are correct and try again.'
        abort(404, description)

    if 'tracked_mod_ids' in session:
        tracked_mod_ids = session['tracked_mod_ids']

    return render_template('games/mod.html', game=game, mod=page_ready_mod, tracked_mod_ids=tracked_mod_ids)


@app.route('/games/<string:game_domain_name>')
@login_required
@get_api_headers
def show_game_page(game_domain_name, headers=None):
    """Show game page with mods hosted by Nexus.
    
    - Nexus API is called to populate Mod categories on page.
    -- Mod Categories: Trending, Latest Added, Latest Updated.
    - Buttons linking to game page on Nexus for further browsing.
    """

    try:
        game = get_game_db(game_domain_name)
    except:
        description = f"Sorry, an issue was encountered retrieving game information.<br>Please check that the requested game domain name: '{game_domain_name}' matches the one used for this game on Nexus and try again."
        abort(404, description)

    mod_categories = [
        {'mod_cat': 'trending', 'section_title':'Trending Mods'}, 
        {'mod_cat': 'latest_added', 'section_title':'Latest Added Mods'}, 
        {'mod_cat': 'latest_updated', 'section_title':'Latest Updated Mods'}
    ]

    for cat in mod_categories:
        nxs_category = get_mods_of_type_nxs(game, cat['mod_cat'], headers=headers)
        
        if nxs_category == "error":
            cat['error'] = True # displays error message in category area on page
        else:
            try:
                db_ready_data = filter_nxs_data(nxs_category, 'mods')
                cat['data'] = db_ready_data
                update_list_mods_db(db_ready_data)
                link_mods_to_game(db_ready_data, game)
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                print(f"Error func: show_game_page({game_domain_name})\nError detail: {e}")

    return render_template('games/game.html', game=game, mod_categories=mod_categories)


@app.route('/games')
def show_all_games_page():
    """Show list of popular games Nexus hosts mods for, and 
    an alphabet menu to see list of games starting with that letter.
    Click a game to go to that game page.
    """ 

    try:
        games_list = get_all_games_db()
    except Exception as e:
        print("Error getting games from db: ", e)
        flash("Problem occurred fetching games list, refresh page to reattempt.", 'warning')
        return render_template('games/all-games.html', games_list=[{'name':"Error"}])

    else:
        return render_template('games/all-games.html', games_list=games_list)


##############################################################################
# Nexus records changing routes

@app.route('/api/games/<string:game_domain_name>/mods/<int:mod_id>/endorsement/<string:endorse_action>')
@login_required
@get_api_headers
def endorse_mod(game_domain_name, mod_id, endorse_action, headers=None):
    """Sends request to Nexus API to change user's endorsement status for the mod 
    with game_domain_name and mod_id to 'Endorsed' or 'Abstained'.
    
    Redirects back to same mod page it was requested from."""

    if endorse_action not in ['endorse', 'abstain']:
        description = "Invalid URL. Mod endorsement request urls must end with '/endorse' or '/abstain'."
        abort(400, description)
    
    endorsement_requested = endorse_mod_nxs(game_domain_name, mod_id, endorse_action, headers=headers)
    # error handling success or failure message flashed from nexus_api.py
    
    if endorse_action == 'endorse' and endorsement_requested:
        session[str(mod_id)] = 'Endorsed'

    if endorse_action == 'abstain' and endorsement_requested:
        session[str(mod_id)] = 'Abstained'

    return redirect(url_for('show_mod_page', game_domain_name=game_domain_name, mod_id=int(mod_id)))


@app.route('/api/games/<string:game_domain_name>/mods/<int:mod_id>/tracking/<string:track_action>')
@login_required
@get_api_headers
def track_mod(game_domain_name, mod_id, track_action, headers=None):
    """Sends request to Nexus API to change user's track tracked mods list on 
    Nexus to include the mod with game_domain_name and mod_id.
    
    Redirects back to same mod page it was requested from."""

    if track_action not in ['add', 'delete']:
        description = "Invalid URL. Mod endorsement request urls must end with '/add' or '/delete'."
        abort(400, description)

    if track_action == 'add' and 'tracked_mod_ids' in session and mod_id in session['tracked_mod_ids']:
        flash("Mod is already tracked by your Nexus account. An already tracked mod can not be tracked again. If this is inaccurate, please go to your Nexus Tracked Mods modpage and click the 'Re-Sync Tracked Mods to Nexus' button so we can display current information.", 'warning')

    if track_action == 'delete' and 'tracked_mod_ids' in session and mod_id not in session['tracked_mod_ids']:
        flash("Mod is already not tracked by your Nexus account. A mod that is not tracked can not be un-tracked. If this is inaccurate, please go to your Nexus Tracked Mods modpage and click the 'Re-Sync Tracked Mods to Nexus' button so we can display current information.", 'warning')
    
    tracking_requested = track_mod_nxs(game_domain_name, mod_id, track_action, headers=headers)
    # error handling success or failure message flashed from nexus_api.py
    
    if tracking_requested:
        update_tracked_mods_from_nexus(g.user.id, headers=headers)
        if "tracked_mod_ids" in session and track_action == 'add' and mod_id not in session["tracked_mod_ids"]:
            session["tracked_mod_ids"].append(mod_id)
        if "tracked_mod_ids" in session and track_action == 'delete' and mod_id in session["tracked_mod_ids"]:
            session["tracked_mod_ids"].remove(mod_id)

    return redirect(url_for('show_mod_page', game_domain_name=game_domain_name, mod_id=int(mod_id)))


##############################################################################
# Homepage and error pages

@app.route('/')
def homepage():
    """Show homepage:

    - anon users: show sign up pitch page 
      (must also be signed in to Nexus SSO or provide personal user 
      account API key for API to function)

    - logged in: redirect to user's profile page 
    """

    if not g.user:
        return render_template('home-anon.html')
        
    empty_modlists = get_empty_modlists(g.user.id)
    modlists_by_game = get_recent_modlists_by_game(g.user.id)

    return render_template('users/profile-user.html', user=g.user, empty_modlists=empty_modlists, modlists_by_game=modlists_by_game)


@app.errorhandler(400)
def bad_request(error):
    message = "The browser (or proxy) sent a request that this server could not understand."

    if error.description == "Invalid Request": 
           error.description = "An error was encountered retrieving data from the Nexus server. Please try again."
    return render_template('errors/http-error.html', error=error, error_message=message), 400


@app.errorhandler(401)
def unauthorized(error):
    message = "The server could not verify that you are authorized to access the URL requested."
    return render_template('errors/http-error.html', error=error, error_message=message), 401


@app.errorhandler(403)
def forbidden(error):
    message = "You don't have the permission to access the requested resource or perform the requested action."
    if message[:10] == error.description[:10]:
        error.description = "The user is authenticated but not authorized to access the requested resource or perform the requested action."
    return render_template('errors/http-error.html', error=error, error_message=message), 403


@app.errorhandler(404)
def not_found(error):
    message = "The requested URL was not found on the server.<br>If you entered the URL manually please check your spelling and try again"

    if error.description in ["Missing", "Missing Resource", "File not found."]: 
           error.description = "An error was encountered retrieving data from the Nexus server. Please try again."
    return render_template('errors/http-error.html', error=error, error_message=message), 404


@app.errorhandler(405)
def method_not_allowed(error):
    message = "The method is not allowed for the requested URL."

    if message[:10] == error.description[:10]: 
           error.description = "Please check the URL and try a different method.<br>If you were trying to submit a form, make sure you're using the correct method (e.g., POST)."
    return render_template('errors/http-error.html', error=error, error_message=message), 405


@app.errorhandler(422)
def unprocessable_entity(error):
    message = "The request was well-formed but was unable to be followed due to semantic errors."

    if error.description == "Could not save the entity.": 
           error.description = "An error was encountered retrieving data from the Nexus server. Please try again."
    return render_template('errors/http-error.html', error=error, error_message=message), 422


@app.errorhandler(500)
def internal_server_error(error):
    message = "The server encountered an internal error and was unable to complete your request.<br>Either the server is overloaded or there is an error in the application."
    return render_template('errors/http-error.html', error=error, error_message=message), 500


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