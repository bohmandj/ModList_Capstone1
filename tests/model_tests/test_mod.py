"""Mod model tests."""

import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Mod, Modlist, Game

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app

class ModModelTestCase(TestCase):
    """Tests for Mod model."""

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
        db.session.execute(db.text("DELETE FROM game_mod"))
        db.session.execute(User.__table__.delete())
        db.session.execute(Modlist.__table__.delete())
        db.session.execute(Mod.__table__.delete())
        db.session.execute(Game.__table__.delete())

        # Create sample user: username, email, password
        u1 = User.signup(
            username="test_user1", 
            email="user1@test.com", 
            password="password1"
        )
        u1.id = 100
        db.session.add(u1)
        db.session.commit()
        self.user1 = db.session.get(User, u1.id)

        # Create sample modlist: name, description, private, user
        ml1 = Modlist.new_modlist(
            name="Test Modlist 1", 
            description="Description of modlist 1", 
            private=False, 
            user=self.user1
        )
        ml1.id = 200
        db.session.add(ml1)
        db.session.commit()
        self.modlist1 = db.session.get(Modlist, ml1.id)

        # Create sample game: id, domain name, name, downloads
        g1 = Game(
            id=300,
            domain_name="test_game",
            name="Test Game",
            downloads=1234
        )
        db.session.add(g1)
        db.session.commit()
        self.game1 = db.session.get(Game, g1.id)

        md1 = Mod(
            id=400,
            name="Test Mod 1",
            summary="A test mod summary.",
            is_nsfw=False,
            updated_timestamp=1234567890,
            uploaded_by="uploader2"
        )
        md1.for_games.append(self.game1)
        db.session.add(md1)
        db.session.commit()
        self.mod1 = db.session.get(Mod, md1.id)

    def tearDown(self):
        """Clean up fouled transactions."""
        db.session.rollback()

    def test_mod_model(self):
        """Basic model test for Mod instance creation."""
        self.assertEqual(self.mod1.name, "Test Mod 1")
        self.assertEqual(self.mod1.summary, "A test mod summary.")
        self.assertIn(self.game1, self.mod1.for_games)

    def test_add_mod_to_modlist(self):
        """Test adding a mod to a modlist."""
        self.modlist1.mods.append(self.mod1)
        db.session.commit()

        # Confirm that modlist now has the mod
        self.assertIn(self.mod1, self.modlist1.mods)
        self.assertEqual(len(self.modlist1.mods), 1)

    def test_remove_mod_from_modlist(self):
        """Test removing a mod from a modlist."""
        self.modlist1.mods.append(self.mod1)
        db.session.commit()

        # Now remove the mod
        self.modlist1.mods.remove(self.mod1)
        db.session.commit()

        # Confirm that modlist no longer has the mod
        self.assertNotIn(self.mod1, self.modlist1.mods)
        self.assertEqual(len(self.modlist1.mods), 0)

    def test_unique_constraint(self):
        """Ensure mod ID is unique and conflicts on duplicates."""
        existing_id = self.mod1.id
        # Attempt to add another mod with the same ID
        duplicate_mod = Mod(
            id=existing_id,
            name="Duplicate Mod",
            summary="Another test mod"
        )
        
        db.session.add(duplicate_mod)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_cascade_delete_modlist_does_not_delete_mod(self):
        """Ensure deleting a modlist does not delete associated mods."""
        # Add mod to modlist
        self.modlist1.mods.append(self.mod1)
        db.session.commit()
        mod_id = self.mod1.id

        # Delete modlist and confirm mod still exists
        db.session.delete(self.modlist1)
        db.session.commit()

        # Mod should still exist after modlist deletion
        self.assertIsNotNone(db.session.get(Mod, mod_id))
        self.assertEqual(self.mod1.id, mod_id)

    def test_mod_relationships(self):
        """Test that mod can relate to multiple modlists."""
        # Create second modlist
        modlist2 = Modlist.new_modlist(
            name="Second Modlist",
            description="A second test modlist",
            private=False,
            user=self.user1
        )
        db.session.add(modlist2)
        db.session.commit()

        # Add mod to both modlists
        self.modlist1.mods.append(self.mod1)
        modlist2.mods.append(self.mod1)
        db.session.commit()

        # Confirm mod is in both modlists
        self.assertIn(self.mod1, self.modlist1.mods)
        self.assertIn(self.mod1, modlist2.mods)

        db.session.delete(modlist2)
        db.session.commit()

