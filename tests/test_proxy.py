import os
import unittest

from flask import url_for
from flask_login import login_user

from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User
from common.status import HTTP_302_FOUND, HTTP_200_OK

os.environ["FLASK_ENV"] = "testing"

HTTP_403_FORBIDDEN = 403
HTTP_401_UNAUTHORIZED = 401


def create_user(
    username="testuser",
    email="testuser@example.com",
    password="password",
    role="developer",
    status="approved",
    confirmed=True,
):
    user = User(
        name="Test User",
        username=username,
        email=email,
        password=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
        status=status,
        confirmed=confirmed,
    )
    db.session.add(user)
    db.session.commit()
    return user


class TestProxyRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(env="testing")
        cls.app.config["SERVER_NAME"] = "localhost"

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

    def test_kibana_unauthenticated_redirects_to_login(self):
        """Unauthenticated user hitting /proxy/kibana is redirected to login"""
        with self.app.test_request_context("/"):
            response = self.client.get(url_for("proxy.kibana"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("login", response.location)

    def test_prometheus_unauthenticated_redirects_to_login(self):
        """Unauthenticated user hitting /proxy/prometheus is redirected to login"""
        with self.app.test_request_context("/"):
            response = self.client.get(url_for("proxy.prometheus"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("login", response.location)

    def test_node_exporter_unauthenticated_redirects_to_login(self):
        """Unauthenticated user hitting /proxy/node-exporter is redirected to login"""
        with self.app.test_request_context("/"):
            response = self.client.get(url_for("proxy.node_exporter"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("login", response.location)

    def test_kibana_viewer_is_blocked(self):
        """Viewer gets 403 on /proxy/kibana"""
        user = create_user(
            username="viewer1", email="viewer1@example.com", role="viewer"
        )
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.kibana"))
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_prometheus_viewer_is_blocked(self):
        """Viewer gets 403 on /proxy/prometheus"""
        user = create_user(
            username="viewer2", email="viewer2@example.com", role="viewer"
        )
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.prometheus"))
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_node_exporter_viewer_is_blocked(self):
        """Viewer gets 403 on /proxy/node-exporter"""
        user = create_user(
            username="viewer3", email="viewer3@example.com", role="viewer"
        )
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.node_exporter"))
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_kibana_developer_is_allowed(self):
        """Developer is redirected to nginx for /proxy/kibana"""
        user = create_user(username="dev1", email="dev1@example.com", role="developer")
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.kibana"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("kibana", response.location)

    def test_prometheus_developer_is_allowed(self):
        """Developer is redirected to nginx for /proxy/prometheus"""
        user = create_user(username="dev2", email="dev2@example.com", role="developer")
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.prometheus"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("prometheus", response.location)

    def test_node_exporter_developer_is_allowed(self):
        """Developer is redirected to nginx for /proxy/node-exporter"""
        user = create_user(username="dev3", email="dev3@example.com", role="developer")
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.node_exporter"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("node-exporter", response.location)

    def test_kibana_admin_is_allowed(self):
        """Admin is redirected to nginx for /proxy/kibana"""
        user = create_user(username="admin1", email="admin1@example.com", role="admin")
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.kibana"))
        self.assertEqual(response.status_code, HTTP_302_FOUND)
        self.assertIn("kibana", response.location)

    def test_auth_kibana_developer_returns_200(self):
        """Auth check for kibana returns 200 for developer"""
        user = create_user(username="dev4", email="dev4@example.com", role="developer")
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.auth_kibana"))
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_auth_kibana_viewer_returns_403(self):
        """Auth check for kibana returns 403 for viewer"""
        user = create_user(
            username="viewer4", email="viewer4@example.com", role="viewer"
        )
        with self.app.test_request_context("/"):
            login_user(user)
            response = self.client.get(url_for("proxy.auth_kibana"))
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_auth_prometheus_unauthenticated_returns_401(self):
        """Auth check for prometheus returns 401 for unauthenticated"""
        with self.app.test_request_context("/"):
            response = self.client.get(url_for("proxy.auth_prometheus"))
        self.assertEqual(response.status_code, HTTP_401_UNAUTHORIZED)


if __name__ == "__main__":
    unittest.main()
