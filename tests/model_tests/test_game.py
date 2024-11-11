"""Game model tests."""

import os
from unittest import TestCase
from sqlalchemy.exc import IntegrityError
from models import db, connect_db, User, Modlist, Mod, Game

os.environ['DATABASE_URL'] = "postgresql:///modlist_test"

from app import app

class GameModelTestCase(TestCase):
    """Tests for Game model."""

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

    def tearDown(self):
        """Rollback session after each test."""
        db.session.rollback()

    def test_game_model(self):
        """Basic test for game model creation and attributes."""
        self.assertIsNotNone(self.game1)
        self.assertEqual(self.game1.name, "Test Game")
        self.assertEqual(self.game1.domain_name, "test_game")
        self.assertEqual(self.game1.downloads, 1234)

    def test_unique_constraint(self):
        """Ensure game ID is unique and conflicts on duplicates."""
        existing_id = self.game1.id
        
        duplicate_game = Game(
            id=existing_id,
            domain_name="duplicate_game",
            name="Duplicate Test Game",
            downloads=5678
        )

        db.session.add(duplicate_game)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_game_mod_relationship(self):
        """Test relationship between game and mods."""
        mod = Mod(
            id=300,
            name="Test Mod",
            summary="A test mod summary.",
            is_nsfw=False,
            updated_timestamp=1234567890,
            uploaded_by="uploader2"
        )
        db.session.add(mod)
        db.session.commit()

        self.game1.subject_of_mods.append(mod)
        db.session.commit()

        # Confirm that the mod is associated with the game
        self.assertIn(mod, self.game1.subject_of_mods)

    def test_game_modlist_relationship(self):
        """Test relationship between game and modlists."""
        modlist = Modlist.new_modlist(
            name="Test Modlist",
            description="A description of the test modlist",
            private=False,
            user=self.user1
        )
        db.session.add(modlist)
        db.session.commit()

        modlist.for_games.append(self.game1)
        db.session.commit()

        # Confirm that the game is associated with the modlist
        self.assertIn(self.game1, modlist.for_games)

    def test_game_delete_cascade_modlist(self):
        """Ensure deleting a modlist does not delete associated game."""
        modlist = Modlist.new_modlist(
            name="Another Modlist",
            description="Another description",
            private=False,
            user=self.user1
        )
        modlist.id = 200
        db.session.add(modlist)
        db.session.commit()

        modlist.for_games.append(self.game1)
        db.session.commit()

        # Delete game and confirm modlist still exists
        modlist_id = modlist.id
        db.session.delete(modlist)
        db.session.commit()

        self.assertIsNone(db.session.get(Modlist, modlist.id))
        self.assertIsNotNone(db.session.get(Game, self.game1.id))

