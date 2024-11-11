"""Tests for routes for the user's tracked mods modlist, 'Nexus Tracked Mods'."""

import os
from unittest import TestCase
from unittest.mock import patch, Mock
from flask import session, get_flashed_messages, g, request
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Modlist, Mod, Game, keep_tracked, game_mod

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app, CURR_USER_KEY

app.config['WTF_CSRF_ENABLED'] = False

class TrackedModlistRoutesTestCase(TestCase):
    """Tests for the user's tracked-mods modlist routes:
	show_tracked_modlist_page(), change_keep_tracked_status()
    """

    @classmethod
    def setUpClass(cls):
        """Create test client and set up the database."""
        cls.app = app
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        db.drop_all()
        db.create_all()

        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        """Clean up the database after tests."""
        db.session.remove()
        cls.app_context.pop()

    def setUp(self):
        """Set up test data for each test."""
        db.session.execute(keep_tracked.delete())
        db.session.execute(game_mod.delete())
        db.session.execute(User.__table__.delete())
        db.session.execute(Modlist.__table__.delete())
        db.session.execute(Mod.__table__.delete())
        db.session.execute(Game.__table__.delete())
        db.session.commit()

        self.password1 = 'password1'
        self.user1 = User.signup(
            username='testuser1',
            email='testuser1@example.com',
            password=self.password1
        )
        self.user1.id = 100
        db.session.add(self.user1)
        db.session.commit()

        new_game = Game(
            id=200, 
            domain_name='test_game_domain',
            name='Test Game Name',
            downloads=12345
        )
        db.session.add(new_game)
        db.session.commit()
        self.game1 = db.session.get(Game, new_game.id)

        tracked_ml = Modlist.new_modlist(
            name='Nexus Tracked Mods', 
            description="This modlist automatically populates with all the mods in your Nexus account's Tracking Centre.", 
            private=True,
            user=self.user1
        )
        tracked_ml.id = 100
        db.session.add(tracked_ml)
        db.session.commit()
        self.tracked_modlist = db.session.get(Modlist, tracked_ml.id)

        self.mod1 = Mod(
            id=301,
            name='Test Mod One',
            summary='Test Mod One Summary',
            is_nsfw= False,
            picture_url='modpic1@test.com',
            updated_timestamp=1234567890,
            uploaded_by='Some Username',
            for_games=[self.game1]
        )
        self.mod2 = Mod(
            id=302,
            name='Test Mod Two',
            summary='Test Mod Two Summary',
            is_nsfw= False,
            picture_url='modpic2@test.com',
            updated_timestamp=1234567890,
            uploaded_by='Some Username',
            for_games=[self.game1]
        )
        db.session.add_all([self.mod1, self.mod2])
        db.session.commit()

        self.tracked_modlist.mods.extend([self.mod1, self.mod2])
        self.user1.keep_tracked.append(self.mod2)
        db.session.commit()

    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()
        with self.client.session_transaction() as session:
            session.clear()


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_tracked_modlist_page_tracked_tab_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test tracked modlist page, 'tracked-mods' tab view for logged-in user."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            # log in user1
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })
            with client.session_transaction() as session:
                self.assertEqual(session[CURR_USER_KEY], self.user1.id)

            response = client.get('/users/modlists/tracked-mods', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.tracked_modlist.name, response.get_data(as_text=True))
            self.assertIn(self.mod1.name, response.get_data(as_text=True))
            self.assertNotIn(self.mod2.name, response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_tracked_modlist_page_keep_tab_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test tracked modlist page, 'keep-tracked' tab view for logged-in user."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            # log in user1
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })
            with client.session_transaction() as session:
                self.assertEqual(session[CURR_USER_KEY], self.user1.id)

            response = client.get('/users/modlists/keep-tracked-mods', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.tracked_modlist.name, response.get_data(as_text=True))
            self.assertNotIn(self.mod1.name, response.get_data(as_text=True))
            self.assertIn(self.mod2.name, response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    @patch('utilities.get_mod_nxs')
    @patch('utilities.get_tracked_mods_nxs')
    def test_show_tracked_modlist_page_tracked_sync_logged_in(self, mock_get_tracked_mods_nxs, mock_get_mod_nxs, mock_tracked_mods_update, mock_games_list_update):
        """Test tracked modlist page, 'Re-Sync Tracked Mods to Nexus' 
        button for 'tracked-sync' route tab function for logged-in user."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        # Prepare the mock return values to avoid external API dependency
        mock_get_tracked_mods_nxs.return_value = [
            { 'mod_id':303, 'domain_name':'test_game_domain' },
            { 'mod_id':302, 'domain_name':'test_game_domain' }
            ] # sync should add mod 303 and remove 301 from tracked mods
        mock_get_mod_nxs.return_value = {
            'mod_id':303,
            'name':'Test Mod Name',
            'summary':'Test Mod Summary',
            'contains_adult_content': False,
            'picture_url':'modpic@test.com',
            'updated_timestamp':1234567890,
            'uploaded_by':'Some Username',
            'status':'published'
        }

        self.assertIn(self.mod1, self.tracked_modlist.mods)
        self.assertIn(self.mod2, self.tracked_modlist.mods)
        self.assertIsNone(db.session.get(Mod, 303))

        with self.client as client:
            # log in user1
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })
            with client.session_transaction() as session:
                self.assertEqual(session[CURR_USER_KEY], self.user1.id)

            response = client.get('/users/modlists/tracked-sync', follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            
            follow_response = client.get(response.location, follow_redirects=True)
            self.assertEqual(follow_response.status_code, 200)

            self.assertIn(self.tracked_modlist.name, follow_response.get_data(as_text=True))
            self.assertNotIn(self.mod1, self.tracked_modlist.mods)
            self.assertNotIn(self.mod1.name, follow_response.get_data(as_text=True))
            self.assertIn(self.mod2, self.tracked_modlist.mods)
            mod3 = db.session.get(Mod, 303)
            self.assertIn(mod3, self.tracked_modlist.mods)
            self.assertIn(mod3.name, follow_response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_add_to_keep_tracked_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test adding 'keep tracked' status to a tracked mod 
        as a logged-in user."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            # log in user1
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })
            with client.session_transaction() as session:
                self.assertEqual(session[CURR_USER_KEY], self.user1.id)

            # Arg that gets added to the route by the 'Add to Keep Tracked' button for redirect purposes
            next_page_arg = f'?next=/users/modlists/tracked-mods'

            # Send request to change tracked status
            response = client.post(f'/users/modlists/keep-tracked-mods/mods/{self.mod1.id}/add{next_page_arg}', follow_redirects=False)
            self.assertEqual(response.status_code, 302)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"Success! '{self.mod1.name}' has been added to your Keep-Tracked list."), flash_messages)
            
            follow_response = client.get(response.location, follow_redirects=True)
            self.assertEqual(follow_response.status_code, 200)
            self.assertIn(self.mod1, self.tracked_modlist.mods)
            self.assertIn(self.mod2, self.tracked_modlist.mods)
            self.assertIn(self.mod1, self.user1.keep_tracked)
            self.assertIn(self.mod2, self.user1.keep_tracked)
            self.assertIn(self.tracked_modlist.name, follow_response.get_data(as_text=True))
            self.assertIn("No mods added to 'Nexus Tracked Mods' modlist yet...", follow_response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_delete_from_keep_tracked_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test deleting 'keep tracked' status from a 'keep tracked' 
        tracked mod as a logged-in user."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            # log in user1
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })
            with client.session_transaction() as session:
                self.assertEqual(session[CURR_USER_KEY], self.user1.id)

            # Arg that gets added to the route by the 'Remove from Keep Tracked' button for redirect purposes
            next_page_arg = f'?next=/users/modlists/keep-tracked-mods'

            # Send request to change tracked status
            response = client.post(f'/users/modlists/keep-tracked-mods/mods/{self.mod2.id}/delete{next_page_arg}', follow_redirects=False)
            self.assertEqual(response.status_code, 302)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"Success! '{self.mod2.name}' has been removed from your Keep-Tracked list."), flash_messages)
            
            follow_response = client.get(response.location, follow_redirects=True)
            self.assertEqual(follow_response.status_code, 200)
            self.assertIn(self.mod1, self.tracked_modlist.mods)
            self.assertIn(self.mod2, self.tracked_modlist.mods)
            self.assertEqual(follow_response.status_code, 200)
            self.assertNotIn(self.mod1, self.user1.keep_tracked)
            self.assertNotIn(self.mod2, self.user1.keep_tracked)
            self.assertIn(self.tracked_modlist.name, follow_response.get_data(as_text=True))
            self.assertIn("No tracked mods marked 'Keep-Tracked' yet...", follow_response.get_data(as_text=True))


    def test_show_tracked_modlist_page_all_tabs_not_logged_in(self):
        """Test tracked modlist page, with all tab options ('tracked-mods', 
        'keep-tracked-mods', 'tracked-sync'), for non-logged-in user."""

        tab_options = ['tracked-mods', 'keep-tracked-mods', 'tracked-sync']
        
        with self.client as client:
            for tab in tab_options:
                response = client.get(f'/users/modlists/{tab}', follow_redirects=False)
                self.assertEqual(response.status_code, 302)
                
                flash_messages = get_flashed_messages(with_categories=True)
                self.assertIn(('danger', "Access unauthorized."), flash_messages)

                follow_response = client.get(response.location, follow_redirects=True)
                self.assertEqual(follow_response.status_code, 200)
                self.assertIn('Username', follow_response.get_data(as_text=True))
                self.assertIn('Password', follow_response.get_data(as_text=True))
                self.assertNotIn(CURR_USER_KEY, session)
                self.assertNotIn('user_api_key', session)


    def test_change_keep_tracked_not_logged_in(self):
        """Test change_keep_tracked_status route, both add and delete, 
        for a non-logged-in user."""

        keep_action_options = ['add', 'delete']
        
        with self.client as client:
            for action in keep_action_options:
                if action == 'add':
                    target_mod_id = self.mod1.id
                elif action == 'delete':
                    target_mod_id = self.mod2.id

                # Send request to change tracked status
                response = client.post(f'/users/modlists/keep-tracked-mods/mods/{target_mod_id}/{action}', follow_redirects=False)
                self.assertEqual(response.status_code, 302) # should get redirected to login page
                
                flash_messages = get_flashed_messages(with_categories=True)
                self.assertIn(('danger', "Access unauthorized."), flash_messages)

                follow_response = client.get(response.location, follow_redirects=True)
                self.assertEqual(follow_response.status_code, 200)
                self.assertIn('Username', follow_response.get_data(as_text=True))
                self.assertIn('Password', follow_response.get_data(as_text=True))
                self.assertNotIn(CURR_USER_KEY, session)
                self.assertNotIn('user_api_key', session)