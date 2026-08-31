"""Shared pytest fixtures.

Tests run against their own database (`attache_test`), never the dev database,
and every test is wrapped in a transaction that is rolled back afterwards — so
tests cannot see each other's data and cannot leave anything behind.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  — imported so Base.metadata knows the tables
from app.config import settings
from app.database import Base, get_db
from app.main import create_app
from app.repositories import user_repo
from app.security import hash_password

TEST_DB_NAME = "attache_test"
_server_url, _dev_db_name = settings.DATABASE_URL.rsplit("/", 1)
TEST_DATABASE_URL = f"{_server_url}/{TEST_DB_NAME}"

# Shared by the user fixtures so tests can log in without repeating it.
TEST_PASSWORD = "password123"


def _create_test_database_if_missing() -> None:
    """CREATE DATABASE attache_test, if it does not already exist.

    Connects to the built-in `postgres` database because you cannot create a
    database from inside the one you are connected to. AUTOCOMMIT is required:
    Postgres refuses CREATE DATABASE inside a transaction block.
    """
    admin_engine = create_engine(f"{_server_url}/postgres", isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    """One engine for the whole test run, with the schema created once."""
    _create_test_database_if_missing()
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    """A session whose writes are always undone when the test ends.

    The session is bound to a single connection holding an open transaction.
    `join_transaction_mode="create_savepoint"` turns the `commit()` calls inside
    the repositories into savepoint releases rather than real commits, so the
    outer rollback still erases everything the test wrote.
    """
    connection = engine.connect()
    transaction = connection.begin()
    TestSession = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def make_client(db_session):
    """Factory for API clients that share the test's rolled-back session.

    A factory rather than a single client because the isolation tests need two
    independent cookie jars — one logged in as each user.
    """
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    clients: list[TestClient] = []

    def _make() -> TestClient:
        client = TestClient(app)
        clients.append(client)
        return client

    yield _make

    for client in clients:
        client.close()
    app.dependency_overrides.clear()


@pytest.fixture()
def client(make_client) -> TestClient:
    """An anonymous API client."""
    return make_client()


def _create_user(db_session, email: str):
    return user_repo.create(
        db_session,
        email=email,
        password_hash=hash_password(TEST_PASSWORD),
    )


@pytest.fixture()
def alice(db_session):
    return _create_user(db_session, "alice@example.com")


@pytest.fixture()
def bob(db_session):
    return _create_user(db_session, "bob@example.com")


def _login(client: TestClient, email: str) -> TestClient:
    response = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
    assert response.status_code == 200, "fixture login failed"
    return client


@pytest.fixture()
def alice_client(make_client, alice) -> TestClient:
    return _login(make_client(), alice.email)


@pytest.fixture()
def bob_client(make_client, bob) -> TestClient:
    return _login(make_client(), bob.email)
