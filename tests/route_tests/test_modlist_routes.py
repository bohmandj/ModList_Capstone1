"""Tests for Modlist routes."""

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
    """Tests for the Modlist routes:
	new_modlist(), modlist_add_mod(), 
    modlist_delete_mod(), edit_modlist(), 
    delete_modlist(), show_modlist_page()
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

    @patch('app.do_games_list_update')
    @patch('app.do_tracked_mods_update')
    def setUp(self, mock_tracked_mods_update, mock_games_list_update):
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
        ) # added to modlist1 in setUp to test deletion route
        self.mod2 = Mod(
            id=302,
            name='Test Mod Two',
            summary='Test Mod Two Summary',
            is_nsfw= True,
            picture_url='modpic2@test.com',
            updated_timestamp=1234567890,
            uploaded_by='Some Username',
            for_games=[self.game1]
        ) # not added to modlist1 in setUp to test addition route
        db.session.add_all([self.mod1, self.mod2])
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
            "name": self.mod2.name, 
            "summary": self.mod2.summary,
            "picture_url": self.mod2.picture_url, 
            "mod_downloads": 1234, 
            "mod_unique_downloads": 1234, 
            "uid": 1234, 
            "mod_id": self.mod2.id,
            "game_id": self.game1.id, 
            "domain_name": self.game1.domain_name, 
            "version": '1.0.0',
            "endorsement_count": 12345, 
            "updated_timestamp": self.mod2.updated_timestamp, 
            "updated_time": '0000-00-00 00:00:00.000000+00:00', 
            "author": self.mod2.uploaded_by,
            "uploaded_by": self.mod2.uploaded_by, 
            "uploaded_users_profile_url": 'users_profile.com', 
            "contains_adult_content": self.mod2.is_nsfw, 
            "status": 'published', 
            "available": True, 
            "endorsement": { 
                "endorse_status": 'Abstained', 
                "timestamp": '0000-00-00 00:00:00.000000+00:00', 
                "version": '1.0.0' 
            }
        }  

        # prevent unnecessary extra login functions
        mock_tracked_mods_update.return_value = None
        mock_games_list_update.return_value = None

        with self.client as client:
            # all modlist routes have @login_required -> log in user1 for testing
            client.post('/login', data={
                'username': self.user1.username,
                'password': self.password1,
                'user_api_key': 'never_sent_does_not_matter'
            })


    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()
        with self.client.session_transaction() as session:
            session.clear()


    def test_new_modlist_success(self):
        """Test successful new modlist creation."""

        new_modlist_name = 'Test Modlist Two'

        with self.client as client:
            response = client.post('/users/modlists/new', data={
                'name':new_modlist_name, 
                'description':"Description of Test Modlist Two",
                'private':False,
                'user':g.user
            }, follow_redirects=False)
            self.assertEqual(response.status_code, 302)
            follow_response = client.get(response.location, follow_redirects=True)

        self.assertEqual(follow_response.status_code, 200)
        new_modlist = db.session.execute(
            db.select(Modlist)
            .where(Modlist.name==new_modlist_name)
        ).scalars().first()
        self.assertIsNotNone(new_modlist)
        self.assertIn(new_modlist, self.user1.modlists)
        self.assertEqual(len(self.user1.modlists), 2)
        self.assertIn(new_modlist.name, follow_response.get_data(as_text=True))
        self.assertIn(self.user1.username, follow_response.get_data(as_text=True))


    def test_new_modlist_duplicate_name(self):
        """Test unsuccessful new modlist creation due to duplicate name."""

        with self.client as client:
            response = client.post('/users/modlists/new', data={
                'name':self.modlist1.name, 
                'description':"Description of Test Modlist Two",
                'private':False,
                'user':g.user
            }, follow_redirects=False)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', f"You already have a modlist named '{self.modlist1.name}', please choose another name."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.user1.modlists), 1)
        self.assertIn('Create New ModList:', response.get_data(as_text=True))


    @patch('app.get_mod_nxs')
    def test_modlist_add_mod_success(self, mock_get_mod_nxs):
        """Test successful addition of a mod to the user's modlist"""

        mock_get_mod_nxs.return_value = self.mock_mod_data     
        self.assertFalse(self.modlist1.has_nsfw)
        self.assertEqual(len(self.modlist1.mods), 1)

        with self.client as client:
            response = client.post(f'/users/modlists/add/mods/{self.mod2.id}', data={'users_modlists':[self.modlist1.id]}, follow_redirects=True)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"{self.mod2.name} was successfully added to: {self.modlist1.name}."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.mod2, self.modlist1.mods)
        self.assertEqual(len(self.modlist1.mods), 2)
        self.assertTrue(self.modlist1.has_nsfw)
        self.assertIn(self.mod2.name, response.get_data(as_text=True))


    @patch('app.get_mod_nxs')
    def test_modlist_add_mod_duplicate(self, mock_get_mod_nxs):
        """Test unsuccessful addition of a mod to the user's 
        modlist that already contains that mod"""

        mock_get_mod_nxs.return_value = self.mock_mod_data
        self.assertEqual(len(self.modlist1.mods), 1)

        with self.client as client:
            response = client.post(f'/users/modlists/add/mods/{self.mod1.id}', data={'users_modlists':[self.modlist1.id]}, follow_redirects=True)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', f"{self.mod1.name} already exists in: '{self.modlist1.name}'."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.modlist1.mods), 1)


    def test_modlist_delete_mod_success(self):
        """Test successful deletion of a mod from the user's modlist"""

        mod1_id = self.mod1.id
        self.assertEqual(len(self.modlist1.mods), 1)
        self.assertIn(self.game1, self.modlist1.for_games)

        with self.client as client:
            response = client.post(f'/users/modlists/{self.modlist1.id}/mods/{self.mod1.id}/delete', data={'users_modlists':[self.modlist1.id]}, follow_redirects=True)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f'{self.mod1.name} successfully removed from {self.modlist1.name}!'), flash_messages)

        self.assertEqual(response.status_code, 200)
        mod_not_deleted_from_db = db.session.get(Mod, mod1_id)
        self.assertIsNotNone(mod_not_deleted_from_db)
        self.assertEqual(len(self.modlist1.mods), 0)
        self.assertEqual(len(self.modlist1.for_games), 0)


    def test_edit_modlist_success(self):
        """Test successful edit of a user's modlist"""

        new_name = 'Edited Modlist'
        new_description = "Edited description"
        new_private_status = True
        self.assertFalse(self.modlist1.name == new_name)
        self.assertFalse(self.modlist1.description == new_description)
        self.assertFalse(self.modlist1.private == new_private_status)

        with self.client as client:
            response = client.post(f'/users/modlists/{self.modlist1.id}/edit', data={
                'name': new_name,
                'description': new_description,
                'private': new_private_status
            }, follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"Success! Edits to '{new_name}' saved."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.modlist1.name, new_name)
        self.assertEqual(self.modlist1.description, new_description)
        self.assertEqual(self.modlist1.private, new_private_status)
        self.assertIn(self.modlist1.name, response.get_data(as_text=True))


    def test_edit_modlist_duplicate_name(self):
        """Test unsuccessful edit of a user's modlist 
        because of duplicate name"""

        original_modlist1_name = self.modlist1.name
        duplicate_name = 'Test Modlist Two'

        modlist2 = Modlist.new_modlist(
            name=duplicate_name, 
            description="Description of Test Modlist Two", 
            private=False,
            user=self.user1
        )
        modlist2.id = 401
        db.session.add(modlist2)
        db.session.commit()

        modlist2.mods.append(self.mod1)
        modlist2.for_games.append(self.game1)
        db.session.commit()

        new_description = "Edited description"
        new_private_status = True
        self.assertFalse(self.modlist1.name == modlist2.name)
        self.assertFalse(self.modlist1.name == duplicate_name)

        with self.client as client:
            response = client.post(f'/users/modlists/{self.modlist1.id}/edit', data={
                'name': duplicate_name,
                'description': new_description,
                'private': new_private_status
            }, follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', f"You already have a modlist named '{duplicate_name}', please choose another name."), flash_messages)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.modlist1.name, original_modlist1_name)
        self.assertFalse(self.modlist1.name == modlist2.name)
        self.assertIn(f"Edit Modlist '{original_modlist1_name}'", response.get_data(as_text=True))


    def test_delete_modlist_success(self):
        """Test successful deletion of a user's modlist"""

        modlist_exists = db.session.get(Modlist, self.modlist1.id)
        self.assertIsNotNone(modlist_exists)
        self.assertIn(self.modlist1, self.mod1.in_modlists)
        self.assertIn(self.modlist1, self.user1.modlists)
        self.assertEqual(len(self.user1.modlists), 1)

        with self.client as client:
            response = client.post(f'/users/modlists/{self.modlist1.id}/delete', follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('success', f"Success! Modlist '{modlist_exists.name}' has been deleted!"), flash_messages)

        self.assertEqual(response.status_code, 200)
        modlist_still_exists = db.session.get(Modlist, modlist_exists.id)
        self.assertIsNone(modlist_still_exists)
        self.assertNotIn(modlist_exists, self.mod1.in_modlists)
        self.assertNotIn(modlist_exists, self.user1.modlists)
        self.assertEqual(len(self.user1.modlists), 0)


    def test_delete_modlist_invalid_user(self):
        """Test unsuccessful deletion of a user's modlist 
        due to user not owning the modlist"""

        user2 = User.signup(
            username='testuser2',
            email='testuser2@example.com',
            password='password2'
        )
        user2.id = 200
        db.session.add(user2)
        self.modlist1.user = user2
        db.session.commit()

        modlist_exists = db.session.get(Modlist, self.modlist1.id)
        self.assertIsNotNone(modlist_exists)
        self.assertIn(self.modlist1, self.mod1.in_modlists)
        self.assertIn(self.modlist1, user2.modlists)
        self.assertEqual(len(user2.modlists), 1)

        with self.client as client:
            response = client.post(f'/users/modlists/{self.modlist1.id}/delete', follow_redirects=True)
        
            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', "A modlist can only be edited or deleted by the owner of the modlist."), flash_messages)

        self.assertEqual(response.status_code, 200)
        modlist_still_exists = db.session.get(Modlist, modlist_exists.id)
        self.assertIsNotNone(modlist_still_exists)
        self.assertIn(self.modlist1, self.mod1.in_modlists)
        self.assertIn(self.modlist1, user2.modlists)
        self.assertEqual(len(user2.modlists), 1)


    def test_delete_modlist_invalid_modlist_name(self):
        """Test unsuccessful deletion of a user's modlist 
        due to modlist being named 'Nexus Tracked Mods'"""

        self.modlist1.name = 'Nexus Tracked Mods'
        db.session.commit()

        modlist_exists = db.session.get(Modlist, self.modlist1.id)
        self.assertIsNotNone(modlist_exists)
        self.assertIn(self.modlist1, self.mod1.in_modlists)
        self.assertIn(self.modlist1, self.user1.modlists)
        self.assertEqual(len(self.user1.modlists), 1)

        with self.client as client:
            response = client.post(f'/users/modlists/{self.modlist1.id}/delete', follow_redirects=True)

            flash_messages = get_flashed_messages(with_categories=True)
            self.assertIn(('danger', "The 'Nexus Tracked Mods' modlist is not editable or deleted."), flash_messages)

        self.assertEqual(response.status_code, 200)
        modlist_still_exists = db.session.get(Modlist, modlist_exists.id)
        self.assertIsNotNone(modlist_still_exists)
        self.assertIn(self.modlist1, self.mod1.in_modlists)
        self.assertIn(self.modlist1, self.user1.modlists)
        self.assertEqual(len(self.user1.modlists), 1)


    def test_show_modlist_page(self):
        """Test show modlist page route"""

        with self.client as client:
            response = client.get(f'/users/{self.user1.id}/modlists/{self.modlist1.id}', follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.modlist1.name, response.get_data(as_text=True))
        self.assertIn(self.modlist1.for_games[0].name, response.get_data(as_text=True))
        self.assertIn(self.mod1.name, response.get_data(as_text=True))
        self.assertIn(self.mod1.summary, response.get_data(as_text=True))
        self.assertIn('Edit Modlist', response.get_data(as_text=True))