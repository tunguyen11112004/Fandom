from uuid import uuid4

from app.main import create_app

client = create_app().test_client()


def test_auth_index_is_not_404():
    r = client.get("/api/be/v1/auth")
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["ok"] is True
    assert "login" in body["data"]["endpoints"]


def test_root_is_the_site():
    r = client.get("/")
    assert r.status_code == 200
    assert b"Fan Hub Plus" in r.data


def test_health_and_api_index():
    assert client.get("/health").status_code == 200
    r = client.get("/api")
    assert r.status_code == 200
    assert r.get_json()["groups"]["auth"] == "/api/be/v1/auth"


def test_register_login_flow():
    email = f"member-{uuid4().hex[:8]}@example.com"
    password = "Matkhau1"
    r = client.post(
        "/api/be/v1/auth/register",
        json={"name": "Thanh Vien", "email": email, "password": password, "password_confirm": password},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    login = client.post("/api/be/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 403
    assert login.get_json()["error"] == "email_unverified"


def test_admin_login():
    r = client.post(
        "/api/be/v1/auth/admin/login",
        json={"email": "admin@fanhubplus.com", "password": "Admin123!"},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    token = r.get_json()["data"]["access_token"]
    me = client.get("/api/be/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.get_json()["data"]["role"] == "admin"


def test_member_cannot_admin_login():
    email = f"user-{uuid4().hex[:8]}@example.com"
    password = "Matkhau1"
    client.post(
        "/api/be/v1/auth/register",
        json={"name": "User", "email": email, "password": password, "password_confirm": password},
    )
    r = client.post("/api/be/v1/auth/admin/login", json={"email": email, "password": password})
    assert r.status_code in (403, 401)
