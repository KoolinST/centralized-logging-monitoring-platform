import unittest
import string
from app.utils.generating import generate_nonce
from unittest.mock import patch, MagicMock
from app.utils.email import send_confirmation_email, send_reset_password
from flask import Flask, session


class TestUtils(unittest.TestCase):
    def test_generate_nonce_length(self):
        nonce = generate_nonce()
        self.assertEqual(len(nonce), 16, "Nonce should be 16 characters long.")

    def test_generate_nonce_characters(self):
        nonce = generate_nonce()
        valid_characters = string.ascii_letters + string.digits
        self.assertTrue(
            all(c in valid_characters for c in nonce),
            "Nonce should only contain alphanumeric characters.",
        )

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    @patch("app.utils.email.logging")
    def test_send_confirmation_email(
        self, mock_logging, mock_commit, mock_url_for, mock_send
    ):
        app = Flask(__name__)
        app.secret_key = "test_secret_key"

        with app.app_context():
            mock_user = MagicMock()
            mock_user.email = "test@example.com"

            send_confirmation_email(mock_user)

            mock_send.assert_called_once()
            mock_commit.assert_called_once()
            self.assertIsNotNone(
                mock_user.email_confirmation_expiry,
                "Email confirmation expiry should be set.",
            )

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    @patch("app.utils.email.logging")
    def test_send_confirmation_email_error(
        self, mock_logging, mock_commit, mock_url_for, mock_send
    ):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.get_email_confirmation_token.return_value = "dummy_token"

        mock_send.side_effect = Exception("Email sending failed")

        app = Flask(__name__)
        app.secret_key = "test_secret_key"

        with app.app_context():
            with app.test_request_context():
                send_confirmation_email(mock_user)

                mock_logging.error.assert_called_with(
                    "Error occurred while sending confirmation email: "
                    "Email sending failed"
                )

                self.assertIn("_flashes", session)
                flashes = session["_flashes"]
                self.assertEqual(len(flashes), 1)
                self.assertEqual(
                    flashes[0][0], "danger"
                )  # Check that the category is 'danger'
                self.assertIn(
                    "An error occurred while sending the confirmation email.",
                    flashes[0][1],
                )  # Check message content

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.logging")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    def test_send_reset_password(
        self, mock_logging, mock_commit, mock_url_for, mock_send
    ):
        app = Flask(__name__)
        app.secret_key = "test_secret_key"

        with app.app_context():
            with app.test_request_context():
                mock_user = MagicMock()
                mock_user.email = "test@example.com"
                mock_user.get_reset_token.return_value = "dummy_token"

                send_reset_password(mock_user)
                mock_send.assert_called_once()
                mock_commit.assert_called_once()
                self.assertNotIn("_flashes", session)

    @patch("app.utils.email.mail.send")
    @patch("app.utils.email.db.session.commit")
    @patch("app.utils.email.url_for")
    @patch("app.utils.email.logging")
    def test_send_reset_password_error(
        self, mock_logging, mock_commit, mock_url_for, mock_send
    ):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.get_reset_token.return_value = "dummy_token"

        mock_send.side_effect = Exception("Email sending failed")

        app = Flask(__name__)
        app.secret_key = "test_secret_key"

        with app.app_context():
            with app.test_request_context():
                send_reset_password(mock_user)
                mock_logging.error.assert_called_with(
                    "Error occurred while sending reset password email: "
                    "Email sending failed"
                )

                self.assertIn("_flashes", session)
                flashes = session["_flashes"]
                self.assertEqual(len(flashes), 1)
                self.assertEqual(flashes[0][0], "danger")
                self.assertIn(
                    "An error occurred while sending the confirmation email.",
                    flashes[0][1],
                )  # Check message content


if __name__ == "__main__":
    unittest.main()
