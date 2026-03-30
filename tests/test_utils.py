import os
import string
import unittest
from unittest.mock import patch, MagicMock

from app import create_app
from app.utils.generating import generate_nonce
from app.utils.email import send_confirmation_email, send_reset_password
from flask import session

os.environ["FLASK_ENV"] = "testing"


class TestGenerateNonce(unittest.TestCase):

    def test_generate_nonce_length(self):
        """Nonce should be 16 characters long"""
        nonce = generate_nonce()
        self.assertEqual(len(nonce), 16)

    def test_generate_nonce_characters(self):
        """Nonce should only contain alphanumeric characters"""
        nonce = generate_nonce()
        valid_characters = string.ascii_letters + string.digits
        self.assertTrue(all(c in valid_characters for c in nonce))

    def test_generate_nonce_uniqueness(self):
        """Two nonces should not be identical"""
        nonces = {generate_nonce() for _ in range(100)}
        self.assertEqual(len(nonces), 100)

    def test_generate_nonce_custom_length(self):
        """Nonce should respect a custom length argument"""
        nonce = generate_nonce(length=32)
        self.assertEqual(len(nonce), 32)


class TestEmailUtils(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(env="testing")

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    def test_send_confirmation_email_success(
        self, mock_url_for, mock_commit, mock_send
    ):
        """send_confirmation_email calls mail.send and commits once"""
        with self.app.app_context():
            with self.app.test_request_context():
                mock_user = MagicMock()
                mock_user.email = "test@example.com"
                mock_user.get_email_confirmation_token.return_value = "dummy_token"

                send_confirmation_email(mock_user)

                mock_send.assert_called_once()
                mock_commit.assert_called_once()

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.rollback")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    def test_send_confirmation_email_error(
        self, mock_url_for, mock_commit, mock_rollback, mock_send
    ):
        """send_confirmation_email rolls back and flashes on mail failure"""
        mock_send.side_effect = Exception("Email sending failed")

        with self.app.app_context():
            with self.app.test_request_context():
                mock_user = MagicMock()
                mock_user.email = "test@example.com"
                mock_user.get_email_confirmation_token.return_value = "dummy_token"

                send_confirmation_email(mock_user)

                mock_rollback.assert_called_once()
                self.assertIn("_flashes", session)
                flashes = session["_flashes"]
                self.assertEqual(len(flashes), 1)
                self.assertEqual(flashes[0][0], "danger")
                self.assertIn(
                    "An error occurred while sending the confirmation email.",
                    flashes[0][1],
                )

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    def test_send_reset_password_success(self, mock_url_for, mock_commit, mock_send):
        """send_reset_password calls mail.send and commits once"""
        with self.app.app_context():
            with self.app.test_request_context():
                mock_user = MagicMock()
                mock_user.email = "test@example.com"
                mock_user.get_reset_token.return_value = "dummy_token"

                send_reset_password(mock_user)

                mock_send.assert_called_once()
                mock_commit.assert_called_once()
                self.assertNotIn("_flashes", session)

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.rollback")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    def test_send_reset_password_error(
        self, mock_url_for, mock_commit, mock_rollback, mock_send
    ):
        """send_reset_password rolls back and flashes on mail failure"""
        mock_send.side_effect = Exception("Email sending failed")

        with self.app.app_context():
            with self.app.test_request_context():
                mock_user = MagicMock()
                mock_user.email = "test@example.com"
                mock_user.get_reset_token.return_value = "dummy_token"

                send_reset_password(mock_user)

                mock_rollback.assert_called_once()
                self.assertIn("_flashes", session)
                flashes = session["_flashes"]
                self.assertEqual(len(flashes), 1)
                self.assertEqual(flashes[0][0], "danger")
                self.assertIn(
                    "An error occurred while sending the password reset email.",
                    flashes[0][1],
                )


if __name__ == "__main__":
    unittest.main()
