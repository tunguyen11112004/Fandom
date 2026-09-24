from uuid import uuid4

from app.main import create_app

client = create_app().test_client()


def _admin_token():
    r = client.post(
        "/api/be/v1/auth/admin/login",
        json={"email": "admin@fanhubplus.com", "password": "Admin123!"},
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    return r.get_json()["data"]["access_token"]


def test_health_and_categories():
    assert client.get("/health").status_code == 200
    r = client.get("/api/be/v1/categories")
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len(r.get_json()["data"]) == 8


def test_member_cannot_admin_content():
    email = f"m-{uuid4().hex[:8]}@example.com"
    client.post(
        "/api/be/v1/auth/register",
        json={"name": "User", "email": email, "password": "Matkhau1", "password_confirm": "Matkhau1"},
    )
    r = client.post("/api/be/v1/admin/contents", json={"category_id": 1, "title": "x", "type": "article"})
    assert r.status_code == 401


def test_admin_content_and_public_read():
    token = _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    cats = client.get("/api/be/v1/categories").get_json()["data"]
    cid = cats[0]["category_id"]
    r = client.post(
        "/api/be/v1/admin/contents",
        headers=h,
        json={
            "category_id": cid,
            "title": f"Demo Article {uuid4().hex[:6]}",
            "type": "article",
            "summary": "hello",
            "status": "published",
            "is_featured": True,
        },
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    content_id = r.get_json()["data"]["content_id"]
    listed = client.get("/api/be/v1/contents")
    assert listed.status_code == 200
    assert listed.get_json()["data"]["meta"]["total"] >= 1
    detail = client.get(f"/api/be/v1/contents/{content_id}")
    assert detail.status_code == 200
    assert "Demo Article" in detail.get_json()["data"]["title"]


def test_feedback_visitor_needs_email():
    r = client.post("/api/be/v1/feedback", json={"type": "suggestion", "subject": "Hi", "message": "Nice"})
    assert r.status_code == 400
    r = client.post(
        "/api/be/v1/feedback",
        json={"type": "suggestion", "subject": "Hi", "message": "Nice", "contact_email": "v@example.com"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)


def test_advanced_filter_requires_login():
    r = client.get("/api/be/v1/contents?sort=popular")
    assert r.status_code == 401
    assert r.get_json()["error"] == "login_required"


def test_category_hub():
    r = client.get("/api/be/v1/categories/1")
    assert r.status_code == 200, r.get_data(as_text=True)
    data = r.get_json()["data"]
    assert "featured" in data
    assert "breadcrumbs" in data


def test_chat_faq_fallback():
    r = client.post("/api/be/v1/chat/messages", json={"message": "What is Fan Hub Plus?"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()["data"]
    assert body["matched"] is True
    assert "session_token" in body
