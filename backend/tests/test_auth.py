"""Auth endpoint tests — the M1 exit criterion, executable.

The two-user tests are the important ones: they are the first check of the
tenancy guarantee in design doc §3.2 (identity comes only from the JWT).
"""

from app.api.deps import COOKIE_NAME
from app.repositories import user_repo
from tests.conftest import TEST_PASSWORD


# --- signup ---------------------------------------------------------------

def test_signup_creates_user_and_returns_it(client):
    response = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "id" in body


def test_signup_never_returns_the_password_hash(client):
    response = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": TEST_PASSWORD},
    )

    assert "password_hash" not in response.json()
    assert "password" not in response.json()


def test_signup_stores_a_hash_not_the_plaintext(client, db_session):
    client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": TEST_PASSWORD},
    )

    user = user_repo.get_by_email(db_session, "new@example.com")
    assert user is not None
    assert user.password_hash != TEST_PASSWORD
    assert user.password_hash.startswith("$argon2")


def test_signup_logs_the_new_user_in(client):
    client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": TEST_PASSWORD},
    )

    assert client.cookies.get(COOKIE_NAME) is not None
    assert client.get("/auth/me").status_code == 200


def test_signup_rejects_a_duplicate_email(client, alice):
    response = client.post(
        "/auth/signup",
        json={"email": alice.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 409


def test_signup_rejects_a_too_short_password(client):
    response = client.post(
        "/auth/signup",
        json={"email": "new@example.com", "password": "short"},
    )

    # Pydantic rejects it before the route body ever runs.
    assert response.status_code == 422


# --- login ----------------------------------------------------------------

def test_login_succeeds_with_correct_credentials(client, alice):
    response = client.post(
        "/auth/login",
        json={"email": alice.email, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    assert response.json()["email"] == alice.email
    assert client.cookies.get(COOKIE_NAME) is not None


def test_login_rejects_a_wrong_password(client, alice):
    response = client.post(
        "/auth/login",
        json={"email": alice.email, "password": "not-the-password"},
    )

    assert response.status_code == 401
    assert client.cookies.get(COOKIE_NAME) is None


def test_login_rejects_an_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 401


def test_login_does_not_reveal_whether_the_email_exists(client, alice):
    """Both failures must look identical, or the API becomes a user directory."""
    wrong_password = client.post(
        "/auth/login",
        json={"email": alice.email, "password": "not-the-password"},
    )
    unknown_email = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": TEST_PASSWORD},
    )

    assert wrong_password.status_code == unknown_email.status_code
    assert wrong_password.json() == unknown_email.json()


# --- /auth/me and session handling ----------------------------------------

def test_me_requires_authentication(client):
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_a_forged_token(client):
    client.cookies.set(COOKIE_NAME, "not.a.real.token")
    assert client.get("/auth/me").status_code == 401


def test_logout_clears_the_session(alice_client):
    assert alice_client.get("/auth/me").status_code == 200

    alice_client.post("/auth/logout")

    assert alice_client.get("/auth/me").status_code == 401


# --- two-user isolation (the M1 exit criterion) ---------------------------

def test_each_user_sees_only_their_own_account(alice_client, bob_client, alice, bob):
    alice_me = alice_client.get("/auth/me").json()
    bob_me = bob_client.get("/auth/me").json()

    assert alice_me["email"] == alice.email
    assert bob_me["email"] == bob.email
    assert alice_me["id"] != bob_me["id"]


def test_one_users_session_never_returns_another_user(alice_client, bob_client):
    """Two live sessions in flight must not bleed into each other."""
    for _ in range(3):
        assert alice_client.get("/auth/me").json()["email"] == "alice@example.com"
        assert bob_client.get("/auth/me").json()["email"] == "bob@example.com"


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
