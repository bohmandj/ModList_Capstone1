"""Tests for Game and Mod routes."""

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
    """Tests for the Game and Mod routes:
	show_all_games_page(), show_game_page(), 
    show_mod_page()
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
        self.user1.id = 100
        db.session.add(self.user1)

        self.game1 = Game(
            id=201, 
            domain_name='test_game_domain',
            name='Test Name Game 1',
            downloads=1111
        )

        self.game2 = Game(
            id=202, 
            domain_name='test_game2_domain',
            name='Test Name Game 2',
            downloads=2222
        )
        db.session.add_all([self.game1, self.game2])
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
        ) # added to modlist1 in setUp to test deletion route
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

        # Prepare the mock mod return value for rendering 
        # mod page to avoid external API dependency
        self.mock_mod_data = {
            "name": 'Test Mod Two', 
            "summary": 'Test Mod Two Summary',
            "picture_url": 'modpic2@test.com', 
            "mod_downloads": 1234, 
            "mod_unique_downloads": 1234, 
            "uid": 1234, 
            "mod_id": 302,
            "game_id": self.game1.id, 
            "domain_name": self.game1.domain_name, 
            "version": '1.0.0',
            "endorsement_count": 12345, 
            "updated_timestamp": 1234567890, 
            "updated_time": '0000-00-00 00:00:00.000000+00:00', 
            "author": 'Some Username',
            "uploaded_by": 'Some Username', 
            "uploaded_users_profile_url": 'users_profile.com', 
            "contains_adult_content": True, 
            "status": 'published', 
            "available": True, 
            "endorsement": { 
                "endorse_status": 'Abstained', 
                "timestamp": '0000-00-00 00:00:00.000000+00:00', 
                "version": '1.0.0' 
            }
        }  


    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()
        with self.client.session_transaction() as session:
            session.clear()


    def test_show_all_games_page_logged_out(self):
        """Test visiting the all-games page while logged out."""

        response = self.client.get(f'/games', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Most Popular Games on Nexus:', response.get_data(as_text=True))
        self.assertIn(self.game1.name, response.get_data(as_text=True))
        self.assertIn(self.game2.name, response.get_data(as_text=True))
        self.assertIn('Sign up', response.get_data(as_text=True))
        self.assertIn('Log in', response.get_data(as_text=True))


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_all_games_page_logged_in(self, mock_tracked_mods_update, mock_games_list_update):
        """Test visiting the all-games page while logged in."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.get(f'/games', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Most Popular Games on Nexus:', response.get_data(as_text=True))
        self.assertIn(self.game1.name, response.get_data(as_text=True))
        self.assertIn(self.game2.name, response.get_data(as_text=True))
        self.assertIn(self.user1.username, response.get_data(as_text=True))


    def test_show_game_page_logged_out(self):
        """Test visiting a game page while logged out."""

        with self.client as client:
            response = client.get(f'/games/{self.game1.domain_name}/mods/{self.mod1.id}', follow_redirects=True)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', "Access unauthorized."), flash_messages)


        self.assertEqual(response.status_code, 200)
        self.assertIn('Welcome back.', response.get_data(as_text=True))
        self.assertIn('Nexus Personal API Key', response.get_data(as_text=True))


    @patch('app.get_mods_of_type_nxs')
    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_game_page_logged_in(self, mock_tracked_mods_update, mock_games_list_update, mock_mods_of_type_nxs):
        """Test visiting a game page while logged in."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None
        mock_mods_of_type_nxs.return_value = [self.mock_mod_data]

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.get(f'/games/{self.game1.domain_name}', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Trending Mods', response.get_data(as_text=True))
        self.assertIn('Latest Added Mods', response.get_data(as_text=True))
        self.assertIn('Latest Updated Mods', response.get_data(as_text=True))
        self.assertIn(self.game1.name, response.get_data(as_text=True))
        self.assertIn(self.mock_mod_data['name'], response.get_data(as_text=True))
        self.assertIn(self.user1.username, response.get_data(as_text=True))


    def test_show_mod_page_logged_out(self):
        """Test visiting a mod page while logged out."""

        with self.client as client:
            response = client.get(f'/games/{self.game1.domain_name}/mods/{self.mod1.id}', follow_redirects=True)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', "Access unauthorized."), flash_messages)


        self.assertEqual(response.status_code, 200)
        self.assertIn('Welcome back.', response.get_data(as_text=True))
        self.assertIn('Nexus Personal API Key', response.get_data(as_text=True))


    @patch('app.get_mod_nxs')
    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_show_mod_page_logged_in(self, mock_tracked_mods_update, mock_games_list_update, mock_get_mod_nxs):
        """Test visiting a mod page while logged in."""

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        # provide mock mod data to prevent external API dependence
        mock_get_mod_nxs.return_value = self.mock_mod_data

        with self.client as client:
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })

            response = client.get(f'/games/{self.game1.domain_name}/mods/{self.mod1.id}', follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(self.game1.name, response.get_data(as_text=True))
            self.assertIn(f"What would you like to do with {self.mock_mod_data['name']}?", response.get_data(as_text=True))
            self.assertIn(f"Add this mod to a modlist!", response.get_data(as_text=True))