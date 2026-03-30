import os
import time
import logging
import unittest
from unittest.mock import patch, MagicMock

from flask import url_for, redirect
from flask_login import login_user

from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User
from common.status import HTTP_302_FOUND, HTTP_200_OK

os.environ["FLASK_ENV"] = "testing"


class TestRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(env="testing")
        cls.app.config["SERVER_NAME"] = "localhost"
        cls.app.logger.setLevel(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def create_user(
        self, username="testuser", email="testuser@example.com", password="password"
    ):
        user = User(
            name="Test User",
            username=username,
            email=email,
            password=bcrypt.generate_password_hash(password).decode("utf-8"),
        )
        db.session.add(user)
        db.session.commit()
        return user

    def test_test_route(self):
        """GET /test returns 200"""
        response = self.client.get("/test")
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_register_authenticated_user(self):
        """Authenticated user is redirected away from register"""
        user = self.create_user()
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("auth.register"))
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("dashboard.dashboard_view", _external=False)
            )

    def test_register_invalid_form(self):
        """Invalid registration form shows validation error"""
        response = self.client.post(
            "/register",
            data={
                "name": "John Doe",
                "username": "",
                "email": "johndoe@example.com",
                "password": "password",
                "confirm_password": "password",
            },
        )
        self.assertIn(b"This field is required.", response.data)

    @patch("app.routes.auth.send_confirmation_email")
    @patch("app.routes.auth.registration_success_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_register_successful(
        self, mock_latency_labels, mock_registration_counter, mock_send_email
    ):
        """Successful registration redirects to email confirmation"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        response = self.client.post(
            "/register",
            data={
                "name": "Test User",
                "username": "testuser",
                "email": "testuser@example.com",
                "password": "password",
                "confirm_password": "password",
            },
        )

        user = User.query.filter_by(username="testuser").first()
        self.assertIsNotNone(user)
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        with self.app.test_request_context("/"):
            self.assertEqual(
                response.location,
                url_for("auth.email_confirmation", _external=False),
            )
        with self.client.session_transaction() as sess:
            flash_message = sess.get("_flashes")[0][1]
            self.assertEqual(
                flash_message,
                "Registration successful! Please check your email "
                "to confirm your account.",
            )
        mock_send_email.assert_called_once()
        mock_registration_counter.assert_called_once()

    @patch("app.routes.auth.registration_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_register_failure(self, mock_latency_labels, mock_failure_counter):
        """Database error during registration redirects back to register"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        with patch(
            "app.routes.auth.db.session.commit",
            side_effect=Exception("Database error"),
        ):
            response = self.client.post(
                "/register",
                data={
                    "name": "Test User",
                    "username": "testuser",
                    "email": "testuser@example.com",
                    "password": "password",
                    "confirm_password": "password",
                },
            )
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("auth.register", _external=False)
            )
            mock_failure_counter.assert_called_once()

    def test_login_authenticated(self):
        """Authenticated user is redirected away from login"""
        user = self.create_user()
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("auth.login"))
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("dashboard.dashboard_view", _external=False)
            )

    def test_login_success(self):
        """Valid credentials for unconfirmed user redirect to email confirmation"""
        self.create_user()
        response = self.client.post(
            "/login",
            data={"email": "testuser@example.com", "password": "password"},
        )
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        with self.app.test_request_context("/"):
            self.assertEqual(
                response.location,
                url_for("auth.email_confirmation", _external=False),
            )

    def test_login_wrong_password(self):
        """Wrong password shows error message"""
        self.create_user()
        response = self.client.post(
            "/login",
            data={"email": "testuser@example.com", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn(
            b"Login unsuccessful. Please check your email and password.",
            response.data,
        )

    @patch("app.routes.auth.db.session.scalar")
    def test_login_database_error(self, mock_scalar):
        """Database error during login shows generic error message"""
        mock_scalar.side_effect = Exception("Database error")
        response = self.client.post(
            "/login",
            data={"email": "test@example.com", "password": "password123"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn(
            "An unexpected error occurred. Please try again.",
            response.data.decode(),
        )

    @patch("app.routes.auth.email_confirmation_success_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_confirm_email_valid_token(self, mock_latency_labels, mock_success_counter):
        """Valid token confirms the user's email"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        new_user = self.create_user()
        token = new_user.get_email_confirmation_token()
        db.session.commit()

        with self.app.test_request_context("/"):
            response = self.client.get(url_for("auth.confirm_email", token=token))
            user = User.query.filter_by(email="testuser@example.com").first()
            self.assertTrue(user.confirmed)
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(response.location, url_for("auth.login", _external=False))
            mock_success_counter.assert_called_once()

    def test_confirm_email_invalid_token(self):
        """Invalid token does not confirm email and redirects to error page"""
        self.create_user()
        with self.app.test_request_context("/"):
            response = self.client.get(
                url_for("auth.confirm_email", token="invalidtoken")
            )
            user = User.query.filter_by(email="testuser@example.com").first()
            self.assertFalse(user.confirmed)
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(
                response.location,
                url_for("password.token_invalid_email", _external=False),
            )

    @patch("app.routes.auth.email_confirmation_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_confirm_email_exception(self, mock_latency_labels, mock_failure_counter):
        """Exception during confirmation redirects to login"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        self.create_user()
        with patch.object(
            User,
            "verify_and_get_user_from_email_token",
            side_effect=Exception("Internal failure"),
        ):
            with self.app.test_request_context("/"):
                response = self.client.get(
                    url_for("auth.confirm_email", token="any_token")
                )
                self.assertEqual(response.status_code, HTTP_302_FOUND)
                self.assertEqual(
                    response.location, url_for("auth.login", _external=False)
                )
                mock_failure_counter.assert_called_once()

    def test_email_confirmation_page(self):
        """GET /email_confirmation returns 200"""
        response = self.client.get("/email_confirmation")
        self.assertEqual(response.status_code, HTTP_200_OK)

    @patch("app.routes.auth.send_confirmation_email")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_resend_confirmation_already_confirmed(
        self, mock_latency_labels, mock_send_email
    ):
        """Resend to already confirmed user does not send email"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        user = self.create_user()
        user.confirm_email()
        db.session.commit()

        response = self.client.post(
            "/resend_confirmation",
            data={"email": "testuser@example.com"},
            follow_redirects=True,
        )
        mock_send_email.assert_not_called()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn(
            "Account already confirmed. Please log in.", response.data.decode()
        )

    @patch("app.routes.auth.email_confirmation_sends_success_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    @patch("app.routes.auth.db.session.scalar")
    @patch("app.routes.auth.send_confirmation_email")
    def test_resend_confirmation_unconfirmed(
        self, mock_send_email, mock_scalar, mock_latency_labels, mock_success_counter
    ):
        """Resend to unconfirmed user sends email and redirects"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        user = self.create_user()
        user.email_confirmation_expiry = int(time.time()) - 4000
        user.confirmed = False
        mock_scalar.return_value = user

        response = self.client.post(
            "/resend_confirmation",
            data={"email": "testuser@example.com"},
            follow_redirects=False,
        )
        mock_send_email.assert_called_once()
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        with self.app.test_request_context("/"):
            self.assertEqual(
                response.location,
                url_for("auth.email_confirmation", _external=False),
            )
        mock_success_counter.assert_called_once()

    @patch("app.routes.auth.email_confirmation_sends_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    @patch("app.routes.auth.db.session.scalar")
    def test_resend_confirmation_too_soon(
        self, mock_scalar, mock_latency_labels, mock_failure_counter
    ):
        """Resend blocked when confirmation was sent recently"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        user = self.create_user()
        user.email_confirmation_expiry = int(time.time())
        user.confirmed = False
        mock_scalar.return_value = user

        response = self.client.post(
            "/resend_confirmation",
            data={"email": "testuser@example.com"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        with self.app.test_request_context("/"):
            self.assertEqual(
                response.location,
                url_for("auth.email_confirmation", _external=False),
            )
        mock_failure_counter.assert_called_once()

    def test_resend_confirmation_unknown_email(self):
        """Resend for unknown email shows error"""
        response = self.client.post(
            "/resend_confirmation",
            data={"email": "nobody@example.com"},
            follow_redirects=True,
        )
        self.assertIn("No account found with that email.", response.data.decode())

    @patch("app.routes.auth.email_confirmation_sends_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_resend_confirmation_exception(
        self, mock_latency_labels, mock_failure_counter
    ):
        """Exception during resend shows generic error message"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        self.create_user()
        with patch(
            "app.routes.auth.send_confirmation_email",
            side_effect=Exception("Database failure"),
        ):
            response = self.client.post(
                "/resend_confirmation",
                data={"email": "testuser@example.com"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIn(
                "An unexpected error occurred. Please try again.",
                response.data.decode(),
            )
            mock_failure_counter.assert_called_once()

    @patch("app.routes.auth.endpoint_latency.labels")
    def test_logout(self, mock_latency_labels):
        """Logout flashes message and redirects to login"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()

        user = self.create_user()
        with self.app.test_request_context("/"):
            login_user(user)
        response = self.client.post("/logout", follow_redirects=True)
        self.assertIn("You have been logged out.", response.data.decode())
        mock_latency_labels.assert_any_call(endpoint="/logout")

    @patch("app.routes.auth.endpoint_latency.labels")
    def test_check_box(self, mock_latency_labels):
        """GET /check-box returns 200"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()
        response = self.client.get("/check-box")
        self.assertEqual(response.status_code, HTTP_200_OK)

    @patch("app.routes.auth.endpoint_latency.labels")
    def test_register_land(self, mock_latency_labels):
        """GET /registerL returns 200"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_label.time.return_value.__enter__.return_value = MagicMock()
        response = self.client.get("/registerL")
        self.assertEqual(response.status_code, HTTP_200_OK)

    @patch("app.routes.auth.generating.generate_nonce")
    @patch("app.routes.auth.oauth.google.authorize_redirect")
    def test_register_google(self, mock_authorize_redirect, mock_generate_nonce):
        """Google OAuth registration redirects to Google"""
        mock_generate_nonce.return_value = "WgRs1dDi0442qSZe"
        with self.app.test_request_context("/"):
            redirect_uri = url_for("auth.google_register_authorized", _external=True)
            mock_authorize_redirect.return_value = redirect(redirect_uri)

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["nonce"] = "WgRs1dDi0442qSZe"

        response = self.client.get("/register/google", follow_redirects=False)
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn(redirect_uri, response.headers["Location"])

    @patch("app.routes.auth.registration_failure_counter.inc")
    @patch("app.routes.auth.oauth.google.authorize_redirect")
    def test_register_google_exception(
        self, mock_authorize_redirect, mock_failure_counter
    ):
        """Exception during Google OAuth redirects to register land"""
        mock_authorize_redirect.side_effect = Exception("OAuth error")
        response = self.client.get("/register/google", follow_redirects=False)
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn(
            url_for("auth.register_land", _external=False),
            response.headers["Location"],
        )
        mock_failure_counter.assert_called_once()

    @patch("app.routes.auth.oauth.google.authorize_access_token")
    @patch("app.routes.auth.oauth.google.get")
    @patch("app.routes.auth.db.session.scalar")
    def test_google_register_authorized_new_user(
        self, mock_scalar, mock_google_get, mock_authorize_access_token
    ):
        """New user via Google OAuth is redirected to setup_password"""
        mock_authorize_access_token.return_value = {"access_token": "fake"}
        mock_google_get.return_value.json.return_value = {
            "email": "newuser@example.com",
            "name": "New User",
        }
        mock_scalar.return_value = None

        with self.client.session_transaction() as sess:
            sess["nonce"] = "test_nonce"

        response = self.client.get("/register/google/authorized")
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("setup_password", response.location)

    @patch("app.routes.auth.oauth.google.authorize_access_token")
    @patch("app.routes.auth.oauth.google.get")
    @patch("app.routes.auth.db.session.scalar")
    def test_google_register_authorized_existing_user(
        self, mock_scalar, mock_google_get, mock_authorize_access_token
    ):
        """Existing user via Google OAuth is redirected to login"""
        mock_authorize_access_token.return_value = {"access_token": "fake"}
        mock_google_get.return_value.json.return_value = {
            "email": "testuser@example.com",
            "name": "Test User",
        }
        mock_scalar.return_value = User(email="testuser@example.com", name="Test User")

        with self.client.session_transaction() as sess:
            sess["nonce"] = "test_nonce"

        response = self.client.get("/register/google/authorized")
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("login", response.location)

    @patch("app.routes.auth.oauth.google.authorize_access_token")
    def test_google_register_authorized_missing_nonce(
        self, mock_authorize_access_token
    ):
        """Missing nonce redirects back to register"""
        mock_authorize_access_token.return_value = {"access_token": "fake"}
        with self.client.session_transaction() as sess:
            sess["nonce"] = None
        response = self.client.get("/register/google/authorized")
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("register", response.location)

    @patch("app.routes.auth.oauth.google.authorize_access_token")
    def test_google_register_authorized_exception(self, mock_authorize_access_token):
        """Exception during Google OAuth callback redirects to register"""
        mock_authorize_access_token.side_effect = Exception("OAuth error")
        with self.client.session_transaction() as sess:
            sess["nonce"] = "test_nonce"
        response = self.client.get("/register/google/authorized")
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("register", response.location)

    def test_setup_password_invalid_session(self):
        """Missing session data redirects to register land"""
        with self.client.session_transaction() as sess:
            sess["oauth_email"] = None
            sess["oauth_name"] = None
        response = self.client.get("/setup_password", follow_redirects=False)
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("registerL", response.location)

    @patch("app.routes.auth.db.session.scalar")
    def test_setup_password_username_taken(self, mock_scalar):
        """Taken username shows error message"""
        mock_scalar.return_value = User(
            username="testuser123", email="existing@example.com"
        )
        with self.client.session_transaction() as sess:
            sess["oauth_email"] = "newuser@example.com"
            sess["oauth_name"] = "New User"

        response = self.client.post(
            "/setup_password",
            data={
                "username": "testuser123",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn("Username already registered.", response.data.decode())

    @patch("app.routes.password.db.session.scalar")
    @patch("app.routes.password.send_reset_password")
    def test_forgot_password_success(self, mock_send_reset_password, mock_scalar):
        """Valid email triggers password reset email"""
        user = self.create_user()
        mock_scalar.return_value = user
        with self.app.test_request_context("/"):
            response = self.client.post(
                "/forgot-password",
                data={"email": "testuser@example.com"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertIn(url_for("auth.check_box"), response.location)
            mock_send_reset_password.assert_called_once_with(user)

    @patch("app.routes.password.db.session.scalar")
    def test_forgot_password_unknown_email(self, mock_scalar):
        """Unknown email shows error"""
        mock_scalar.return_value = None
        response = self.client.post(
            "/forgot-password",
            data={"email": "nobody@example.com"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn(
            "No account found with that email address.", response.data.decode()
        )

    def test_forgot_password_empty_email(self):
        """Empty email shows warning"""
        response = self.client.post(
            "/forgot-password", data={"email": ""}, follow_redirects=True
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn("Please enter your email address.", response.data.decode())

    @patch("app.routes.password.db.session.scalar")
    def test_forgot_password_too_soon(self, mock_scalar):
        """Rate limit blocks reset request made within 1 hour"""
        user = self.create_user()
        user.password_reset_expiry = int(time.time()) - 1800
        mock_scalar.return_value = user
        response = self.client.post(
            "/forgot-password",
            data={"email": "testuser@example.com"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn(
            "You can request a new password reset email after 1 hour.",
            response.data.decode(),
        )

    def test_reset_password_authenticated_user_redirected(self):
        """Authenticated user accessing reset password is redirected"""
        user = self.create_user()
        self.client.post(
            "/login",
            data={"email": "testuser@example.com", "password": "password"},
        )
        with self.app.test_request_context("/"):
            response = self.client.get(
                url_for("password.reset_password", token="fake-token")
            )
            self.assertIn(url_for("password.token_invalid"), response.location)

    def test_reset_password_invalid_token(self):
        """Invalid token redirects to token_invalid page"""
        with self.app.test_request_context("/"):
            response = self.client.get(
                url_for("password.reset_password", token="invalid-token")
            )
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(
                response.location,
                url_for("password.token_invalid", _external=False),
            )

    def test_reset_password_token_already_used(self):
        """Already used token redirects to token_invalid page"""
        user = self.create_user()
        user.password_reset_used = True
        token = user.get_reset_token()
        db.session.commit()

        with self.app.test_request_context("/"):
            response = self.client.get(
                url_for("password.reset_password", token=token),
                follow_redirects=True,
            )
            self.assertIn("This token has already been used.", response.data.decode())

    def test_reset_password_valid_token_invalid_form(self):
        """Valid token with empty form shows validation error"""
        user = self.create_user()
        token = user.get_reset_token()
        db.session.commit()

        with self.app.test_request_context("/"):
            response = self.client.post(
                url_for("password.reset_password", token=token),
                data={"password": "", "confirm_password": ""},
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIn("This field is required.", response.data.decode())

    def test_reset_password_valid_token_valid_form(self):
        """Valid token with valid form resets password and redirects to login"""
        user = self.create_user()
        token = user.get_reset_token()
        db.session.commit()

        with self.app.test_request_context("/"):
            response = self.client.post(
                url_for("password.reset_password", token=token),
                data={"password": "newpassword", "confirm_password": "newpassword"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(response.location, url_for("auth.login", _external=False))


if __name__ == "__main__":
    unittest.main()
