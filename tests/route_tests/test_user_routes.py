"""Tests for User routes."""

import os
from unittest import TestCase
from unittest.mock import patch, Mock
from flask import session, get_flashed_messages, g
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Modlist, Mod, Game, game_mod, game_modlist, modlist_mod

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app, CURR_USER_KEY

app.config['WTF_CSRF_ENABLED'] = False

class UserRoutesTestCase(TestCase):
    """Tests for the User routes:
	homepage(), show_user_page(),
	edit_profile(), edit_password(),
	delete_user()
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
        db.session.execute(game_mod.delete())
        db.session.execute(game_modlist.delete())
        db.session.execute(modlist_mod.delete())
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
        self.user1.id = 101

        self.password2 = 'password2'
        self.user2 = User.signup(
            username='testuser2',
            email='testuser2@example.com',
            password=self.password2
        )
        self.user2.id = 102
        db.session.add_all([self.user1, self.user2])

        self.game1 = Game(
            id=200, 
            domain_name='test_game_domain',
            name='Test Game Name',
            downloads=12345
        )
        db.session.add(self.game1)
        db.session.commit()

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
        db.session.add(self.mod1)
        db.session.commit()

        self.modlist1 = Modlist.new_modlist(
            name='Test Modlist One', 
            description="Description of Test Modlist One", 
            private=False,
            user=self.user1
        )
        self.modlist1.id = 400
        db.session.add(self.modlist1)
        db.session.commit()

        self.modlist1.mods.append(self.mod1)
        self.modlist1.for_games.append(self.game1)
        db.session.commit()


    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()
        with self.client.session_transaction() as session:
            session.clear()


    def test_homepage_logged_out(self):
        """Test visiting homepage while logged-out"""

        response = self.client.get('/', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("New to ModList?", response.get_data(as_text=True)) # should render new user pitch page


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_homepage_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test visiting homepage for logged-in user"""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.get('/', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.user1.username, response.get_data(as_text=True))
            self.assertIn(self.game1.name, response.get_data(as_text=True))
            self.assertIn(self.modlist1.name, response.get_data(as_text=True))
            self.assertIn(self.mod1.name, response.get_data(as_text=True))
            self.assertIn("Edit Profile", response.get_data(as_text=True))
            self.assertIn("Nexus Tracked Mods", response.get_data(as_text=True))
            self.assertIn("Create New Modlist", response.get_data(as_text=True))


    def test_show_user_page_logged_out(self):
        """Test visiting a user profile page while logged-out"""

        response = self.client.get(f'/users/{self.user1.id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user1.username, response.get_data(as_text=True))
        self.assertIn(self.game1.name, response.get_data(as_text=True))
        self.assertIn(self.modlist1.name, response.get_data(as_text=True))
        self.assertIn(self.mod1.name, response.get_data(as_text=True))
        self.assertNotIn("Edit Profile", response.get_data(as_text=True))
        self.assertNotIn("Nexus Tracked Mods", response.get_data(as_text=True))
        self.assertNotIn("Create New Modlist", response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_user_page_self_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test visiting your own user page while logged-in"""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.get(f'/users/{self.user1.id}', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.user1.username, response.get_data(as_text=True))
            self.assertIn(self.game1.name, response.get_data(as_text=True))
            self.assertIn(self.modlist1.name, response.get_data(as_text=True))
            self.assertIn(self.mod1.name, response.get_data(as_text=True))
            self.assertIn("Edit Profile", response.get_data(as_text=True))
            self.assertIn("Nexus Tracked Mods", response.get_data(as_text=True))
            self.assertIn("Create New Modlist", response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_user_page_other_profile_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test visiting profile page of some other user while logged-in"""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user2.username,
                'password': self.password2,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.get(f'/users/{self.user1.id}', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.user1.username, response.get_data(as_text=True))
            self.assertIn(self.game1.name, response.get_data(as_text=True))
            self.assertIn(self.modlist1.name, response.get_data(as_text=True))
            self.assertIn(self.mod1.name, response.get_data(as_text=True))
            self.assertNotIn("Edit Profile", response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_edit_profile_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test editing user profile details for logged-in user"""

        new_username = 'EditedUsername'
        new_email = 'edit@email.com'
        new_hide_nsfw = 'false'
        self.assertFalse(self.user1.username == new_username)
        self.assertFalse(self.user1.email == new_email)
        self.assertFalse(self.user1.hide_nsfw == new_hide_nsfw)

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.post('/users/edit', data={
                'username':new_username,
                'email':new_email,
                'hide_nsfw':new_hide_nsfw,
                'current_password':self.password1
            }, follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"Success! Edits to {new_username} saved."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user1.username, new_username)
        self.assertEqual(self.user1.email, new_email)
        self.assertFalse(self.user1.hide_nsfw)
        self.assertIn(self.user1.username, response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_edit_password_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test editing user profile password for logged-in user"""

        existing_hash = self.user1.password
        new_password = 'edited_password'
        self.assertFalse(self.password1 == new_password)

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.post('/users/password', data={
                'new_password':new_password,
                'new_confirm':new_password,
                'current_password':self.password1
            }, follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', "Success! New password saved."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user1.password == existing_hash)
        self.assertIn(self.user1.username, response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_delete_user_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test deleting user profile of logged-in user"""

        username = self.user1.username
        user_id = self.user1.id

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })
            self.assertIn(CURR_USER_KEY, session)
            self.assertIn('user_api_key', session)

            response = client.post('/users/delete', follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"Success! User account '{username}' has been deleted!"), flash_messages)

            self.assertNotIn(CURR_USER_KEY, session)
            self.assertNotIn('user_api_key', session)

        self.assertEqual(response.status_code, 200)
        user1_exists = db.session.get(User, user_id)
        self.assertIsNone(user1_exists)
        self.assertIn("New to ModList?", response.get_data(as_text=True)) # should render new user pitch page