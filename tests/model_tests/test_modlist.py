"""Modlist model tests."""

import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Modlist, Mod, Game

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app

class ModlistModelTestCase(TestCase):
    """Tests for Modlist model."""

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
        """Set up sample data for each test."""
        db.session.execute(User.__table__.delete())
        db.session.execute(Modlist.__table__.delete())
        db.session.execute(Mod.__table__.delete())
        db.session.execute(Game.__table__.delete())

        # Create sample user: username, email, password
        u1 = User.signup(
            "test_user1", 
            "user1@test.com", 
            "password1"
        )
        u1.id = 100
        db.session.add(u1)
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
        """Rollback session after each test."""
        db.session.rollback()

    def test_modlist_model(self):
        """Basic test for modlist model creation and attributes."""
        self.assertIsNotNone(self.modlist1)
        self.assertEqual(self.modlist1.name, "Test Modlist 1")
        self.assertEqual(self.modlist1.description, "Description of modlist 1")
        self.assertFalse(self.modlist1.has_nsfw)
        self.assertEqual(self.modlist1.user_id, self.user1.id)

    def test_modlist_timestamp_update(self):
        """Test if the modlist timestamp updates correctly."""
        old_timestamp = self.modlist1.last_updated
        self.modlist1.update_mlist_tstamp()
        db.session.commit()

        self.assertGreater(self.modlist1.last_updated, old_timestamp)

    def test_modlist_mark_nsfw(self):
        """Test if the modlist is marked as NSFW if it contains NSFW mods."""
        # Create an NSFW mod
        nsfw_mod = Mod(
            id=201,
            name="NSFW Mod",
            summary="A NSFW test mod",
            is_nsfw=True,
            updated_timestamp=1234567890,
            uploaded_by="uploader1"
        )

        db.session.add(nsfw_mod)
        db.session.commit()

        # Add NSFW mod to modlist and mark modlist NSFW
        self.modlist1.mods.append(nsfw_mod)
        self.modlist1.mark_nsfw_if_nsfw(nsfw_mod)
        db.session.commit()

        self.assertTrue(self.modlist1.has_nsfw)

    def test_modlist_user_relationship(self):
        """Test if the modlist belongs to the correct user."""
        self.assertEqual(self.modlist1.user.id, self.user1.id)
        self.assertIn(self.modlist1, self.user1.modlists)

    def test_modlist_mod_relationship(self):
        """Test relationship between modlist and mods."""
        mod1 = Mod(
            id=202,
            name="Mod1",
            summary="A sample mod",
            is_nsfw=False,
            updated_timestamp=1234567890,
            uploaded_by="uploader2"
        )
        mod2 = Mod(
            id=203,
            name="Mod2",
            summary="Another sample mod",
            is_nsfw=False,
            updated_timestamp=1234567890,
            uploaded_by="uploader3"
        )

        db.session.add_all([mod1, mod2])
        db.session.commit()

        self.modlist1.mods.extend([mod1, mod2])
        db.session.commit()

        self.assertEqual(len(self.modlist1.mods), 2)
        self.assertIn(mod1, self.modlist1.mods)
        self.assertIn(mod2, self.modlist1.mods)

    def test_modlist_game_relationship(self):
        """Test relationship between modlist and games."""
        game1 = Game(
            id=300,
            domain_name="test_game",
            name="Test Game",
            downloads=1234
        )
        db.session.add(game1)
        db.session.commit()

        # Associate modlist with game
        self.modlist1.for_games.append(game1)
        db.session.commit()

        self.assertEqual(len(self.modlist1.for_games), 1)
        self.assertIn(game1, self.modlist1.for_games)

    def test_modlist_cascade_delete_user(self):
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
