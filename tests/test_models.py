import os
import time
import unittest

from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User

os.environ["FLASK_ENV"] = "testing"


class TestUserModel(unittest.TestCase):
    """Test Cases for User Model"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(env="testing")
        cls.app.config["SERVER_NAME"] = "localhost"

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.user = User(
            name="Test User",
            username="testuser",
            email="testuser@example.com",
            password=bcrypt.generate_password_hash("password").decode("utf-8"),
        )
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_check_password_correct(self):
        """check_password returns True for correct password"""
        self.assertTrue(self.user.check_password("password"))

    def test_check_password_incorrect(self):
        """check_password returns False for wrong password"""
        self.assertFalse(self.user.check_password("wrongpassword"))

    def test_set_password_updates_hash(self):
        """set_password replaces the password hash"""
        self.user.set_password("newpassword")
        db.session.commit()
        self.assertTrue(self.user.check_password("newpassword"))
        self.assertFalse(self.user.check_password("password"))

    def test_get_reset_token_returns_token(self):
        """get_reset_token returns a non-empty string"""
        token = self.user.get_reset_token()
        db.session.commit()
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_get_reset_token_sets_expiry(self):
        """get_reset_token sets password_reset_expiry on the user"""
        before = int(time.time())
        self.user.get_reset_token()
        db.session.commit()
        self.assertIsNotNone(self.user.password_reset_expiry)
        self.assertGreaterEqual(self.user.password_reset_expiry, before)

    def test_verify_reset_token_valid(self):
        """verify_and_get_user_from_reset_token returns user for valid token"""
        token = self.user.get_reset_token()
        db.session.commit()
        result = User.verify_and_get_user_from_reset_token(token)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.user.id)

    def test_verify_reset_token_invalid(self):
        """verify_and_get_user_from_reset_token returns None for invalid token"""
        result = User.verify_and_get_user_from_reset_token("invalidtoken")
        self.assertIsNone(result)

    def test_verify_reset_token_wrong_type(self):
        """verify_and_get_user_from_reset_token returns None for token of wrong type"""
        token = self.user.get_email_confirmation_token()
        db.session.commit()
        result = User.verify_and_get_user_from_reset_token(token)
        self.assertIsNone(result)

    def test_invalidate_reset_token(self):
        """invalidate_reset_token marks token as used and clears it"""
        self.user.get_reset_token()
        self.user.invalidate_reset_token()
        db.session.commit()
        self.assertTrue(self.user.password_reset_used)
        self.assertIsNone(self.user.password_reset_token)

    def test_reset_password_reset_status(self):
        """reset_password_reset_status clears all reset fields"""
        self.user.get_reset_token()
        self.user.invalidate_reset_token()
        db.session.commit()
        self.user.reset_password_reset_status()
        db.session.commit()
        self.assertFalse(self.user.password_reset_used)
        self.assertIsNone(self.user.password_reset_token)
        self.assertIsNone(self.user.password_reset_expiry)

    def test_get_email_confirmation_token_returns_token(self):
        """get_email_confirmation_token returns a non-empty string"""
        token = self.user.get_email_confirmation_token()
        db.session.commit()
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_get_email_confirmation_token_sets_expiry(self):
        """get_email_confirmation_token sets email_confirmation_expiry on the user"""
        before = int(time.time())
        self.user.get_email_confirmation_token()
        db.session.commit()
        self.assertIsNotNone(self.user.email_confirmation_expiry)
        self.assertGreaterEqual(self.user.email_confirmation_expiry, before)

    def test_verify_email_token_valid(self):
        """verify_and_get_user_from_email_token returns user for valid token"""
        token = self.user.get_email_confirmation_token()
        db.session.commit()
        result = User.verify_and_get_user_from_email_token(token)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.user.id)

    def test_verify_email_token_invalid(self):
        """verify_and_get_user_from_email_token returns None for invalid token"""
        result = User.verify_and_get_user_from_email_token("invalidtoken")
        self.assertIsNone(result)

    def test_verify_email_token_wrong_type(self):
        """verify_and_get_user_from_email_token returns None for token of wrong type"""
        token = self.user.get_reset_token()
        db.session.commit()
        result = User.verify_and_get_user_from_email_token(token)
        self.assertIsNone(result)

    def test_confirm_email(self):
        """confirm_email sets confirmed to True and clears token fields"""
        self.user.get_email_confirmation_token()
        db.session.commit()
        self.assertFalse(self.user.confirmed)
        self.user.confirm_email()
        db.session.commit()
        self.assertTrue(self.user.confirmed)
        self.assertIsNone(self.user.email_confirmation_token)
        self.assertIsNone(self.user.email_confirmation_expiry)

    def test_confirm_email_idempotent(self):
        """confirm_email can be called twice without error"""
        self.user.confirm_email()
        db.session.commit()
        self.user.confirm_email()
        db.session.commit()
        self.assertTrue(self.user.confirmed)

    def test_reset_token_cannot_confirm_email(self):
        """A password reset token cannot be used for email confirmation"""
        token = self.user.get_reset_token()
        db.session.commit()
        result = User.verify_and_get_user_from_email_token(token)
        self.assertIsNone(result)

    def test_email_token_cannot_reset_password(self):
        """An email confirmation token cannot be used for password reset"""
        token = self.user.get_email_confirmation_token()
        db.session.commit()
        result = User.verify_and_get_user_from_reset_token(token)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
