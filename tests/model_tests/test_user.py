"""User model tests."""

import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Modlist, Mod, Game

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app

class UserModelTestCase(TestCase):
    """Tests for User model."""

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
        """Add sample data for each test."""
        db.session.execute(User.__table__.delete())
        db.session.execute(Modlist.__table__.delete())
        db.session.execute(Mod.__table__.delete())
        db.session.execute(Game.__table__.delete())

        # Create sample user: username, email, password
        u1 = User.signup(
            "test_user1", 
            "u1@test.com", 
            "test_password1"
        )
        u1.id = 100
        db.session.commit()
        self.user1 = db.session.get(User, u1.id)

        # Create sample modlist: name, description, private, user
        m1 = Modlist.new_modlist(
            "Test Modlist 1", 
            "Description of modlist 1", 
            False, 
            self.user1
        )
        m1.id = 200
        db.session.add(m1)
        db.session.commit()
        self.modlist1 = db.session.get(Modlist, m1.id)


    def tearDown(self):
        """Clean up fouled transactions."""
        db.session.rollback()

    def test_user_model(self):
        """Does basic model work, and are defaults set correctly?"""
        self.assertIsNotNone(self.user1)
        self.assertEqual(self.user1.username, "test_user1")
        self.assertTrue(self.user1.hide_nsfw)  # Default hide_nsfw should be True

    def test_user_signup(self):
        """Test user signup with hashed password."""
        u2 = User.signup("test_user2", "u2@test.com", "test_password2")
        db.session.commit()
        
        self.assertIsNotNone(u2.id)
        self.assertNotEqual(u2.password, "test_password2")  # Password should be hashed

        # Check for None or empty password
        with self.assertRaises(Exception):
            User.signup("test_user3", "u3@test.com", None)
        with self.assertRaises(Exception):
            User.signup("test_user4", "u4@test.com", "")

    def test_user_authentication(self):
        """Test user authentication."""
        u = User.authenticate("test_user1", "test_password1")
        self.assertEqual(u.id, self.user1.id)

        # Test incorrect password
        u = User.authenticate("test_user1", "wrong_password")
        self.assertFalse(u)

        # Test non-existent user
        u = User.authenticate("wrong_username", "test_password1")
        self.assertFalse(u)

        # Test None and empty values
        u = User.authenticate(None, None)
        self.assertFalse(u)
        u = User.authenticate("", "")
        self.assertFalse(u)

    def test_user_modlist_relationship(self):
        """Test user and modlist relationship."""

        self.assertEqual(len(self.user1.modlists), 1)
        self.assertEqual(self.user1.modlists[0].name, "Test Modlist 1")

    def test_unique_constraints(self):
        """Test unique constraints on username and email."""
        # Attempt to add user with duplicate username
        with self.assertRaises(IntegrityError):
            User.signup(
                "test_user1", 
                "new_email@test.com", 
                "password"
            )
            db.session.commit()
        db.session.rollback()

        # Attempt to add user with duplicate email
        with self.assertRaises(IntegrityError):
            User.signup(
                "new_user", 
                "u1@test.com", 
                "password"
            )
            db.session.commit()
        db.session.rollback()

    def test_user_delete_cascade_modlist(self):
        """Ensure deleting a user cascades deletion to their modlists."""
        user1_id = self.user1.id
        modlist1_id = self.modlist1.id

        # Ensure modlist exists
        self.assertTrue(
            db.session.execute(
                db.select(Modlist)
                .where(Modlist.user_id==user1_id)
                .where(Modlist.id==modlist1_id)
            ).scalars().first()
        )

        # Delete user and confirm modlist deletion
        db.session.delete(self.user1)
        db.session.commit()

        self.assertIsNone(db.session.get(User, user1_id))
        self.assertIsNone(
            db.session.execute(
                db.select(Modlist)
                .where(Modlist.user_id==user1_id)
                .where(Modlist.id==modlist1_id)
            ).scalars().first()
        )

