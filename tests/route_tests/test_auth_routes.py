"""Tests for authentication routes."""

import os
from unittest import TestCase
from unittest.mock import patch, Mock
from flask import session, get_flashed_messages, g
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Modlist, Mod, Game

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app, CURR_USER_KEY

app.config['WTF_CSRF_ENABLED'] = False

class AuthRoutesTestCase(TestCase):
    """Tests for the authentication routes:
	signup(), login(), logout()
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
        db.session.add(self.user1)
        db.session.commit()

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

    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()


    def test_signup_success(self):
        """Test successful signup."""
        username = 'testuser2'
        email = 'testuser2@example.com'
        password = 'password2'
        response = self.client.post('/signup', data={
            'username': username,
            'email': email,
            'password': password,
            'confirm' : password
        })

        self.assertEqual(response.status_code, 302)
        user = db.session.execute(
            db.select(User)
            .where(User.username==username)
        ).scalars().first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, email)


    def test_signup_duplicate_username(self):
        """Test signup with a duplicate username."""
    
        existing_user = db.session.execute(
            db.select(User)
            .where(User.username == self.user1.username)
            .where(User.email == self.user1.email)
        ).scalars().first()
        self.assertIsNotNone(existing_user) # user from setUp exists in db

        email = 'another@example.com'
        with self.client as client:
            response = client.post('/signup', data={
                'username': self.user1.username,  # Duplicate username
                'email': email,
                'password': 'password123',
                'confirm': 'password123'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn("Join ModList", response.get_data(as_text=True)) # should render signup page

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', 'Username already taken'), flash_messages)

            duplicate_user = db.session.execute(
                db.select(User)
                .where(User.username == self.user1.username)
                .where(User.email == 'unique_email@example.com')
            ).scalars().first()
            self.assertIsNone(duplicate_user)


    def test_signup_duplicate_email(self):
        """Test signup with a duplicate email."""

        existing_user = db.session.execute(
            db.select(User)
            .where(User.username == self.user1.username)
            .where(User.email == self.user1.email)
        ).scalars().first()
        self.assertIsNotNone(existing_user) # user from setUp exists in db

        username = 'unique_username'
        with self.client as client:
            response = client.post('/signup', data={
                'username': username,
                'email': self.user1.email,  # Duplicate email
                'password': 'password123',
                'confirm': 'password123'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn('Join ModList', response.get_data(as_text=True)) # should render signup page

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', "Email already used - each email can only be used on one account"), flash_messages)

            duplicate_user = db.session.execute(
                db.select(User)
                .where(User.username == 'unique_username')
                .where(User.email == self.user1.email)
            ).scalars().first()
            self.assertIsNone(duplicate_user)


    @patch('utilities.get_mod_nxs')
    @patch('utilities.get_tracked_mods_nxs')
    @patch('app.get_all_games_nxs')
    def test_login_success(self, mock_get_all_games_nxs, mock_get_tracked_mods_nxs, mock_get_mod_nxs):
        """Test successful login."""
        
        # Prepare the mock return values to avoid external API dependency
        mock_get_all_games_nxs.return_value = [{
            'id':200, 
            'domain_name':'test_game_domain',
            'name':'Test Game Name',
            'downloads':12345,
            'unnecessary_category':'unnecessary'
        }]
        mock_get_tracked_mods_nxs.return_value = [{
            'mod_id':201,
            'domain_name':'test_domain_name'
        }]
        mock_get_mod_nxs.return_value = {
            'mod_id':201,
            'name':'Test Mod Name',
            'summary':'Test Mod Summary',
            'contains_adult_content': False,
            'picture_url':'modpic@test.com',
            'updated_timestamp':1234567890,
            'uploaded_by':'Some Username',
            'status':'published'
        }
        
        login_data = {
            'username': self.user1.username,
            'password': self.password1,
            'user_api_key': 'never_sent_does_not_matter'
        }
        
        # Perform the login POST request
        with self.client as client:
            response = client.post('/login', data=login_data, follow_redirects=False)
            self.assertEqual(response.status_code, 302)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', "Hello, testuser1! Welcome back."), flash_messages)
            
            follow_response = client.get(response.location, follow_redirects=True)
            self.assertEqual(follow_response.status_code, 200)
            self.assertIn('Hello', follow_response.get_data(as_text=True))
            self.assertIn(CURR_USER_KEY, session)
            self.assertIn('user_api_key', session)


    def test_login_failure(self):
        """Test login with incorrect credentials."""

        login_data = {
            'username': 'wrong_user',
            'password': 'wrong_password',
            'user_api_key': 'never_sent_does_not_matter'
        }
        
        # Perform the login POST request
        with self.client as client:
            response = client.post('/login', data=login_data, follow_redirects=False)
            self.assertEqual(response.status_code, 200)
            
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', "Invalid credentials."), flash_messages)

            self.assertIn('Welcome back.', response.get_data(as_text=True))
            self.assertNotIn(CURR_USER_KEY, session)
            self.assertNotIn('user_api_key', session)


    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def test_logout(self, mock_tracked_mods_update, mock_games_list_update):
        """Test logout functionality."""

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

            # use logout route
            response = client.get('/logout', follow_redirects=False)
            self.assertEqual(response.status_code, 302)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', "Logout successful!"), flash_messages)

            follow_response = client.get(response.location, follow_redirects=True)
            self.assertEqual(follow_response.status_code, 200)
            self.assertIn('Welcome back.', follow_response.get_data(as_text=True))

            with client.session_transaction() as session:
                self.assertNotIn(CURR_USER_KEY, session)
                self.assertNotIn('user_api_key', session)