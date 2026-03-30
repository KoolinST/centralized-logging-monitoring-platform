"""
Test Factory to make fake objects for testing Users
"""

import factory
from factory.fuzzy import FuzzyChoice
import time
from app import db
from app.models.user import User
from app import bcrypt


class UserFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Creates fake Users"""

    class Meta:
        """Persistent class for factory"""

        model = User
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"

    id = factory.Sequence(lambda n: n)
    name = factory.Faker("name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")
    role = FuzzyChoice(["admin", "developer", "viewer"])
    status = FuzzyChoice(["pending", "approved", "rejected"])
    confirmed = factory.Faker("boolean", chance_of_getting_true=50)
    last_login = factory.LazyFunction(lambda: int(time.time()))
    password_reset_token = None
    password_reset_used = False
    password_reset_expiry = None
    email_confirmation_token = None
    email_confirmation_expiry = None

    @factory.lazy_attribute
    def password(self):
        raw_password = "Password123!"
        return bcrypt.generate_password_hash(raw_password).decode("utf-8")
