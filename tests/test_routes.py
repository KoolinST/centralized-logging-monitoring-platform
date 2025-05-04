import os
import logging
import unittest
from flask import url_for, get_flashed_messages, redirect
from unittest.mock import patch, MagicMock
from flask_login import login_user
from app.extensions import db, bcrypt
from app import create_app
from app.models.user import User
from common import status
from dotenv import load_dotenv
import time
from common.status import HTTP_302_FOUND, HTTP_200_OK

load_dotenv()
os.environ["FLASK_ENV"] = "testing"
DATABASE_URI = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)


class TestUser(unittest.TestCase):
    """Test Cases for User Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        cls.app = create_app(env="testing")
        cls.app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
        cls.app.config["SERVER_NAME"] = "localhost"
        cls.app.logger.setLevel(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        with cls.app.app_context():
            db.session.remove()

    def setUp(self):
        """This runs before each test"""
        self.client = self.app.test_client()
        self.app.app_context().push()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        """This runs after each test"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def create_user(
        self, username="testuser", email="testuser@example.com", password="password"
    ):
        """Helper function to create and commit a user"""
        user = User(
            name="Test User",
            username=username,
            email=email,
            password=bcrypt.generate_password_hash(password).decode("utf-8"),
        )
        db.session.add(user)
        db.session.commit()
        return user

    def test_test_template(self):
        """Test case for testing"""
        with self.app.app_context():
            response = self.client.get("/test")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ---------------- TEST REGISTER ----------------

    def test_register_authenticated_user(self):
        """Test if an authenticated user is redirected to the dashboard page"""
        user = self.create_user()
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("auth.register"))
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("dashboard.dashboard_view", _external=False)
            )

    def test_register_invalid_form(self):
        """Test when the form submission is invalid"""
        with self.app.app_context():
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
    def test_register_successful_user(
        self, mock_latency_labels, mock_registration_counter, mock_send_email
    ):
        """Test successful registration"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        data = {
            "name": "Test User",
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "password",
            "confirm_password": "password",
        }

        with self.app.app_context():
            response = self.client.post("/register", data=data)
            user = User.query.filter_by(username="testuser").first()
            self.assertIsNotNone(user)
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            with self.app.test_request_context("/"):
                self.assertEqual(
                    response.location,
                    url_for("auth.email_confirmation", _external=False),
                )

            with self.app.app_context():
                with self.client.session_transaction() as session:
                    flash_message = session.get("_flashes")[0][1]
                    self.assertEqual(
                        flash_message, "Registration successful. Please log in."
                    )
                mock_send_email.assert_called_once()
                mock_registration_counter.assert_called_once()
                mock_label.time.assert_called_once()

    @patch("app.routes.auth.registration_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_register_failure(self, mock_latency_labels, mock_failure_counter):
        """Simulate a failure during user registration"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        data = {
            "name": "Test User",
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "password",
            "confirm_password": "password",
        }

        with patch(
            "app.routes.auth.db.session.commit", side_effect=Exception("Database error")
        ):
            with self.app.app_context():
                response = self.client.post("/register", data=data)
                self.assertEqual(response.status_code, HTTP_302_FOUND)
                self.assertEqual(
                    response.location, url_for("auth.register", _external=False)
                )

                mock_failure_counter.assert_called_once()
                mock_label.time.assert_called_once()

    # ---------------- TEST LOGIN ----------------

    def test_login_authenticated(self):
        """Test if an authenticated user is redirected to the dashboard page"""
        user = self.create_user()
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("auth.login"))
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("dashboard.dashboard_view", _external=False)
            )

    def test_login_with_good_form(self):
        """Test if user logged with form is redirected to the dashboard page"""
        user = self.create_user()
        with self.app.test_request_context("/"):
            response = self.client.post(
                "/login",
                data={
                    "email": "testuser@example.com",
                    "password": "password",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("dashboard.dashboard_view", _external=False)
            )

    def test_login_with_wrong_form(self):
        """Test if user logged with form is redirected to the dashboard page"""
        user = self.create_user()
        with self.app.test_request_context("/"):
            response = self.client.post(
                "/login",
                data={
                    "email": "testuser@example.com",
                    "password": "wrpassword",
                },
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(
                b"Login Unsuccessful. Please check your email and password.",
                response.data,
            )

    @patch("app.db.session.scalar")
    def test_login_error(self, mock_scalar):
        """Test when any errors occur in login form"""
        mock_scalar.side_effect = Exception("Database error")
        with self.app.test_client() as client:
            response = client.post(
                "/login", data={"email": "test@example.com", "password": "password123"}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("An error occurred: Database error", response.data.decode())

    # ---------------- TEST EMAIL CONFIRMATION ----------------

    @patch("app.routes.auth.email_confirmation_success_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    @patch("app.routes.auth.send_confirmation_email")
    def test_confirm_email(
        self, mock_send_email, mock_latency_labels, mock_success_counter
    ):
        """Test confirmation email by user using unique link"""
        with self.app.app_context():
            new_user = self.create_user()
            self.token = new_user.get_email_confirmation_token()
            mock_label = MagicMock()
            mock_latency_labels.return_value = mock_label
            mock_timer = MagicMock()
            mock_label.time.return_value.__enter__.return_value = mock_timer
            with self.app.test_request_context("/"):
                response = self.client.get(
                    url_for("auth.confirm_email", token=self.token)
                )

                user = User.query.filter_by(email="testuser@example.com").first()
                self.assertTrue(user.confirmed)
                self.assertEqual(response.status_code, HTTP_302_FOUND)
                self.assertEqual(
                    response.location, url_for("auth.login", _external=False)
                )
                mock_success_counter.assert_called_once()
                mock_label.time.assert_called_once()

    def test_confirm_email_error(self):
        """Test confirmation email by user using unique link with invalid token"""
        with self.app.app_context():
            new_user = self.create_user()
            user = User.query.filter_by(email="testuser@example.com").first()
            self.assertFalse(user.confirmed)
            self.token = "invalidtoken"

            with self.app.test_request_context("/"):
                response = self.client.get(
                    url_for("auth.confirm_email", token=self.token)
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
    @patch("app.routes.auth.send_confirmation_email")
    def test_confirm_email_exception(
        self, mock_send_email, mock_latency_labels, mock_failure_counter
    ):
        """Simulate internal failure during email confirmation"""
        with self.app.app_context():
            new_user = self.create_user()
            self.token = "valid_token_that_will_fail"
            mock_label = MagicMock()
            mock_latency_labels.return_value = mock_label
            mock_timer = MagicMock()
            mock_label.time.return_value.__enter__.return_value = mock_timer

            with patch.object(
                User,
                "verify_and_get_user_from_email_token",
                side_effect=Exception("Internal failure"),
            ):
                with self.app.test_request_context("/"):
                    response = self.client.get(
                        url_for("auth.confirm_email", token=self.token)
                    )

                    user = User.query.filter_by(email="testuser@example.com").first()
                    self.assertFalse(user.confirmed)
                    self.assertEqual(response.status_code, HTTP_302_FOUND)
                    self.assertEqual(
                        response.location,
                        url_for("auth.login", _external=False),
                    )

                    mock_failure_counter.assert_called_once()
                    mock_label.time.assert_called_once()

    def test_email_confirmation(self):
        """Test route for user_confirmation communicate"""
        with self.app.app_context():
            response = self.client.get("/email_confirmation")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("app.routes.auth.send_confirmation_email")
    @patch("app.routes.auth.email_confirmation_success_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_resend_confirmation_confirmed(
        self, mock_latency_labels, mock_success_counter, mock_send_email
    ):
        """Test resend confirmation email to already confirmed user"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        user = self.create_user()
        user.confirm_email()
        with self.app.app_context():
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
        self, mock_send_email, mock_scalar, mock_latency_labels, mock_failure_counter
    ):
        """Test resend confirmation email to already confirmed user"""
        with self.app.app_context():
            user = self.create_user()
            user.email_confirmation_expiry = time.time() - 4000
            user.confirmed = False
            mock_label = MagicMock()
            mock_latency_labels.return_value = mock_label
            mock_timer = MagicMock()
            mock_label.time.return_value.__enter__.return_value = mock_timer
            mock_scalar.return_value = user
            response = self.client.post(
                "/resend_confirmation",
                data={"email": "testuser@example.com"},
                follow_redirects=False,
            )
            mock_send_email.assert_called_once()
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                response.location,
                url_for("auth.email_confirmation", _external=False),
            )
            mock_failure_counter.assert_called_once()
            mock_label.time.assert_called_once()

    @patch("app.routes.auth.email_confirmation_sends_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    @patch("app.routes.auth.db.session.scalar")
    def test_resend_confirmation_unconfirmed_error(
        self, mock_scalar, mock_latency_labels, mock_failure_counter
    ):
        """Test resend confirmation email to unconfirmed user with error"""
        with self.app.app_context():
            user = self.create_user()
            user.email_confirmation_expiry = time.time()
            user.confirmed = False
            mock_label = MagicMock()
            mock_latency_labels.return_value = mock_label
            mock_timer = MagicMock()
            mock_label.time.return_value.__enter__.return_value = mock_timer
            mock_scalar.return_value = user
            response = self.client.post(
                "/resend_confirmation",
                data={"email": "testuser@example.com"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, status.HTTP_302_FOUND)
            self.assertEqual(
                response.location,
                url_for("password.token_invalid_email", _external=False),
            )
            mock_failure_counter.assert_called_once()
            mock_label.time.assert_called_once()

    @patch("app.db.session.scalar")
    @patch("app.utils.email.mail.send")
    def test_resend_confirmation_undefined_user(self, mock_send_email, mock_scalar):
        """Test resend confirmation email to undefined user"""
        mock_scalar.return_value = None
        with self.app.test_client() as client:
            response = self.client.post(
                "/resend_confirmation",
                data={"email": "test@example.com"},
                follow_redirects=True,
            )
            mock_send_email.assert_not_called()
            self.assertIn("No account found with that email.", response.data.decode())

    @patch("app.routes.auth.email_confirmation_sends_failure_counter.inc")
    @patch("app.routes.auth.endpoint_latency.labels")
    def test_resend_email_exception(self, mock_latency_labels, mock_failure_counter):
        """Simulate internal failure during resend email confirmation"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        with self.app.app_context():
            user = self.create_user()
            data = {"email": "testuser@example.com"}
            with patch(
                "app.routes.auth.send_confirmation_email",
                side_effect=Exception("DataBase failure"),
            ):
                response = self.client.post(
                    url_for("auth.resend_confirmation"),
                    data=data,
                    follow_redirects=True,
                )

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertIn(
                    "An error occurred while processing", response.data.decode()
                )

                mock_failure_counter.assert_called_once()
                mock_label.time.assert_called_once()

    # ---------------- TEST LOGOUT ----------------

    @patch("app.routes.auth.endpoint_latency.labels")
    def test_logout(self, mock_latency_labels):
        """Test that the user is logged out and redirected to login page"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        with self.app.app_context():
            user = self.create_user()
            with self.app.test_request_context("/"):
                login_user(user)
            response = self.client.post("/logout", follow_redirects=True)

            self.assertIn("You have been logged out.", response.data.decode())
            mock_latency_labels.assert_any_call(endpoint="/logout")
            self.assertTrue(mock_label.time.called)

    # ---------------- TEST STATIC PAGES ----------------

    @patch("app.routes.auth.endpoint_latency.labels")
    def test_check_box(self, mock_latency_labels):
        """Test if check-box route is working correctly"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        with self.app.app_context():
            response = self.client.get("/check-box")
            self.assertEqual(response.status_code, HTTP_200_OK)
            mock_label.time.assert_called_once()

    @patch("app.routes.auth.endpoint_latency.labels")
    def test_register_land(self, mock_latency_labels):
        """Test if register_land route is working correctly"""
        mock_label = MagicMock()
        mock_latency_labels.return_value = mock_label
        mock_timer = MagicMock()
        mock_label.time.return_value.__enter__.return_value = mock_timer
        with self.app.app_context():
            response = self.client.get("/registerL")
            self.assertEqual(response.status_code, HTTP_200_OK)
            mock_label.time.assert_called_once()

    # ---------------- TEST GOOGLE OAUTH ----------------

    @patch("app.utils.generating.generate_nonce")
    @patch("app.oauth.google.authorize_redirect")
    def test_register_google(self, mock_authorize_redirect, mock_generate_nonce):
        """Test that the user is redirected to the Google OAuth login page."""
        mock_generate_nonce.return_value = "WgRs1dDi0442qSZe"
        with self.app.test_request_context("/"):
            redirect_uri = url_for("auth.google_register_authorized", _external=True)
            mock_authorize_redirect.return_value = redirect(redirect_uri)

        with self.client.session_transaction() as sess:
            sess.clear()
            sess["nonce"] = mock_generate_nonce.return_value
        response = self.client.get("/register/google", follow_redirects=False)

        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn(redirect_uri, response.headers["Location"])
        mock_authorize_redirect.assert_called_once_with(
            redirect_uri, nonce=mock_generate_nonce.return_value
        )

    @patch("app.utils.generating.generate_nonce")
    @patch("app.oauth.google.authorize_redirect")
    @patch(
        "app.routes.auth.registration_failure_counter.inc"
    )  # Patch the failure counter
    def test_register_google_with_error(
        self, mock_failure_counter, mock_authorize_redirect, mock_generate_nonce
    ):
        """Test that an exception during Google registration is handled correctly."""

        mock_generate_nonce.return_value = "WgRs1dDi0442qSZe"
        redirect_uri = url_for("auth.google_register_authorized", _external=True)
        mock_authorize_redirect.side_effect = Exception(
            "Error during Google registration"
        )

        with self.app.test_request_context("/"):
            with self.client.session_transaction() as sess:
                sess.clear()
                sess["nonce"] = mock_generate_nonce.return_value

            response = self.client.get("/register/google", follow_redirects=False)
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertIn(
                url_for("auth.register_land", _external=False),
                response.headers["Location"],
            )
            mock_failure_counter.assert_called_once()
            follow_response = self.client.get(response.location)
            self.assertIn(
                "Error during Google registration",
                follow_response.data.decode("utf-8"),
            )

    @patch("app.oauth.google.authorize_access_token")
    @patch("app.oauth.google.parse_id_token")
    @patch("app.oauth.google.get")
    @patch("app.models.user")
    def test_google_register_authorized(
        self,
        mock_user_query,
        mock_google_get,
        mock_parse_id_token,
        mock_authorize_access_token,
    ):
        """Test the google_register_authorized route."""

        mock_token = {
            "access_token": "fake_access_token",
            "id_token": "fake_id_token",
        }
        mock_user_info = {"email": "testuser@example.com", "name": "Test User"}

        mock_authorize_access_token.return_value = mock_token
        mock_parse_id_token.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "1234567890",
            "email": "testuser@example.com",
        }
        mock_google_get.return_value.json.return_value = mock_user_info
        mock_user_query.return_value.first.return_value = None

        with self.client.session_transaction() as sess:
            sess["nonce"] = "test_nonce"

        response = self.client.get("/register/google/authorized")

        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("setup_password", response.location)

    @patch("app.oauth.google.authorize_access_token")
    @patch("app.oauth.google.parse_id_token")
    @patch("app.oauth.google.get")
    @patch("app.models.user")
    def test_google_register_authorized_missing_nonce(
        self,
        mock_user_query,
        mock_google_get,
        mock_parse_id_token,
        mock_authorize_access_token,
    ):
        """Test the google_register_authorized route with missing nonce"""

        mock_token = {
            "access_token": "fake_access_token",
            "id_token": "fake_id_token",
        }
        mock_user_info = {"email": "testuser@example.com", "name": "Test User"}

        mock_authorize_access_token.return_value = mock_token
        mock_parse_id_token.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "1234567890",
            "email": "testuser@example.com",
        }
        mock_google_get.return_value.json.return_value = mock_user_info
        mock_user_query.return_value.first.return_value = None

        with self.client.session_transaction() as sess:
            sess["nonce"] = None

        response = self.client.get("/register/google/authorized")

        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("register", response.location)

    @patch("app.oauth.google.authorize_access_token")
    @patch("app.oauth.google.parse_id_token")
    @patch("app.oauth.google.get")
    @patch("app.db.session.scalar")
    def test_google_register_authorized_existing_user(
        self,
        mock_session_scalar,
        mock_google_get,
        mock_parse_id_token,
        mock_authorize_access_token,
    ):
        """Test if the user already exists in the database."""

        mock_token = {
            "access_token": "fake_access_token",
            "id_token": "fake_id_token",
        }
        mock_user_info = {"email": "testuser@example.com", "name": "Test User"}

        mock_authorize_access_token.return_value = mock_token
        mock_parse_id_token.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "1234567890",
            "email": "testuser@example.com",
        }
        mock_google_get.return_value.json.return_value = mock_user_info
        mock_user = User(email="testuser@example.com", name="Test User")
        mock_session_scalar.return_value = mock_user

        with self.client.session_transaction() as sess:
            sess["nonce"] = "test_nonce"

        response = self.client.get("/register/google/authorized")

        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("login", response.location)

    @patch("app.oauth.google.authorize_access_token")
    @patch("app.oauth.google.get")
    @patch("app.models.user")
    def test_google_register_authorized_exception(
        self, mock_user_query, mock_google_get, mock_authorize_access_token
    ):
        """Test that an exception during Google registration is handled correctly."""
        mock_authorize_access_token.side_effect = Exception("OAuth error")
        with self.client.session_transaction() as sess:
            sess["nonce"] = "test_nonce"  # Valid nonce in session
        response = self.client.get("/register/google/authorized")

        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("register", response.location)

        with self.client as client:
            response = client.get(response.location)

            flashed_messages = [message for message in get_flashed_messages()]
            self.assertIn(
                "An error occurred during Google registration: OAuth error",
                flashed_messages,
            )

    # ---------------- TEST SETUP PASSWORD ----------------

    @patch("app.models.user")
    @patch("app.bcrypt.generate_password_hash")
    def test_setup_password_valid(self, mock_bcrypt, mock_user_query):
        """Test the setup password route with a valid form submission."""

        mock_user_query.return_value = None
        mock_bcrypt.return_value = b"hashed_password"

        with self.client.session_transaction() as sess:
            sess["oauth_email"] = "testuser@example.com"
            sess["oauth_name"] = "Test User"

        form_data = {
            "username": "testuser123",
            "password": "securepassword123",
            "confirm_password": "securepassword123",
        }

        response = self.client.post(
            "/setup_password", data=form_data, follow_redirects=True
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn(
            "Registration successful. You are now logged in.",
            response.data.decode("utf-8"),
        )

    def test_setup_password_invalid_session(self):
        """Test when the session is invalid or expired."""

        with self.client.session_transaction() as sess:
            sess["oauth_email"] = None
            sess["oauth_name"] = None
        response = self.client.get("/setup_password", follow_redirects=False)

        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("registerL", response.location)
        follow_response = self.client.get(response.location)
        self.assertIn(
            "Session expired or invalid. Please authenticate again.",
            follow_response.data.decode("utf-8"),
        )

    @patch("app.db.session.scalar")
    def test_setup_password_username_taken(self, mock_db):
        """Test when the submitted username is already taken."""
        mock_user = User(username="testuser123", email="existinguser@example.com")
        mock_db.return_value = mock_user
        with self.client.session_transaction() as sess:
            sess["oauth_email"] = "testuser@example.com"
            sess["oauth_name"] = "Test User"

        form_data = {
            "username": "testuser123",
            "password": "securepassword123",
            "confirm_password": "securepassword123",
        }

        response = self.client.post(
            "/setup_password", data=form_data, follow_redirects=True
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertIn("Username already registered.", response.data.decode("utf-8"))

    @patch("app.db.session.scalar")
    @patch("app.routes.password.send_reset_password")
    def test_forgot_password_successful(self, mock_send_reset_password, mock_db):
        """Test forgot password route with existing email"""
        user = self.create_user()
        mock_db.return_value = user
        with self.app.test_request_context("/"):
            response = self.client.post(
                "/forgot-password",
                data={"email": "testuser@example.com"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertIn(url_for("auth.check_box"), response.location)
            mock_send_reset_password.assert_called_once_with(user)

    @patch("app.db.session.scalar")
    @patch("app.routes.password.send_reset_password")
    def test_forgot_password_email_not_found(self, mock_send_reset_password, mock_db):
        """Test forgot password route with undefined email"""
        mock_db.return_value = None
        with self.app.test_request_context("/"):
            response = self.client.post(
                "/forgot-password",
                data={"email": "nouser@example.com"},
                follow_redirects=True,
            )
            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIn(
                "No account found with that email address.",
                response.data.decode("utf-8"),
            )

    @patch("app.db.session.scalar")
    def test_forgot_password_no_email_entered(self, mock_scalar):
        """Test forgot password route when no email is entered."""
        with self.app.test_request_context("/"):
            response = self.client.post(
                "/forgot-password", data={"email": ""}, follow_redirects=True
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIn(
                "Please enter your email address.", response.data.decode("utf-8")
            )

    @patch("app.db.session.scalar")
    def test_forgot_password_too_soon(self, mock_scalar):
        """Test when reset request was made less than 1 hour ago."""
        user = self.create_user()
        with self.app.test_request_context("/"):
            user.password_reset_expiry = int(time.time()) - 1800  # 30 minutes ago
            mock_scalar.return_value = user

            response = self.client.post(
                "/forgot-password",
                data={"email": "testuser@example.com"},
                follow_redirects=True,
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertIn(
                "You can request a new password reset email after 1 hour.",
                response.data.decode("utf-8"),
            )

    def test_reset_password_with_authenticated_user(self):
        """Test reset password by authenticated_user using unique link"""
        with self.app.app_context():
            new_user = self.create_user()
            user = User.query.filter_by(email="testuser@example.com").first()

            with self.app.test_request_context("/"):
                self.client.post(
                    "/login",
                    data=dict(email="testuser@example.com", password="password"),
                )
                response = self.client.get(
                    url_for("password.reset_password", token="fake-token")
                )
                self.assertIn(url_for("dashboard.dashboard_view"), response.location)

    def test_reset_password_authenticated_user(self):
        """Test reset password by authenticated_user using unique link"""
        with self.app.app_context():
            new_user = self.create_user()
            user = User.query.filter_by(email="testuser@example.com").first()

            with self.app.test_request_context("/"):
                self.client.post(
                    "/login",
                    data=dict(email="testuser@example.com", password="password"),
                )
                response = self.client.get(
                    url_for("password.reset_password", token="fake-token")
                )
                self.assertIn(url_for("dashboard.dashboard_view"), response.location)

    @patch("app.models")
    def test_reset_password_invalid_token(self, mock_verify_token):
        """Test case when the token is invalid."""
        mock_verify_token.return_value = None  # Simulate invalid token
        with self.app.test_request_context("/"):
            response = self.client.get(
                url_for("password.reset_password", token="invalid-token")
            )
            self.assertEqual(response.status_code, HTTP_302_FOUND)
            self.assertEqual(
                response.location, url_for("password.token_invalid", _external=False)
            )

    @patch("app.models.user")
    def test_reset_password_token_already_used(self, mock_db):
        """Test reset password when the token is already used"""
        with self.app.app_context():
            new_user = self.create_user()
            user = User.query.filter_by(email="testuser@example.com").first()
            user.password_reset_used = True  # Mark the token as already used

            valid_token = user.get_reset_token()
            with self.app.test_request_context("/"):
                response = self.client.get(
                    url_for("password.reset_password", token=valid_token),
                    follow_redirects=True,
                )

                self.assertIn(
                    "This token is expired or has already been used.",
                    response.data.decode("utf-8"),
                )

    def test_reset_password_valid_token_invalid_form(self):
        """Test reset password with a valid token but invalid form submission"""
        with self.app.app_context():
            new_user = self.create_user()
            user = User.query.filter_by(email="testuser@example.com").first()
            valid_token = user.get_reset_token()
            with self.app.test_request_context("/"):
                response = self.client.get(
                    url_for("password.reset_password", token=valid_token)
                )
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertIn("Enter your new password", response.data.decode("utf-8"))
                form_data = {"password": "", "confirm_password": ""}
                response = self.client.post(
                    url_for("password.reset_password", token=valid_token),
                    data=form_data,
                )
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertIn("This field is required.", response.data.decode("utf-8"))

    def test_reset_password_valid_token_valid_form(self):
        """Test reset password with a valid token and valid form submission"""
        with self.app.app_context():
            new_user = self.create_user()
            user = User.query.filter_by(email="testuser@example.com").first()
            valid_token = user.get_reset_token()

            with self.app.test_request_context("/"):
                response = self.client.get(
                    url_for("password.reset_password", token=valid_token)
                )
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertIn("Enter your new password", response.data.decode("utf-8"))

                response = self.client.post(
                    url_for("password.reset_password", token=valid_token),
                    data={
                        "password": "testpassword",
                        "confirm_password": "testpassword",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(response.status_code, HTTP_302_FOUND)
                self.assertEqual(
                    response.location, url_for("auth.login", _external=False)
                )
