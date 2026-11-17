import re
import uuid

from app.ai_service import create_mock_plan
from app.schemas import GeneratedPlan, IdeaIn

IDEA = "An app that helps students track their daily expenses and savings"


def email():
    return f"{uuid.uuid4().hex[:8]}@example.com"


def signup(c, mail=None, password="password123"):
    mail = mail or email()
    r = c.post("/register", data={"name": "Test User", "email": mail, "password": password}, follow_redirects=False)
    assert r.status_code == 303, r.text
    return mail


def generate_and_save(c, public=False):
    r = c.post("/generate", data={"idea": IDEA})
    assert r.status_code == 200
    plan_json = re.search(r'name="plan_json" value="([^"]*)"', r.text).group(1)
    import html
    plan_json = html.unescape(plan_json)
    data = {"original_idea": IDEA, "plan_json": plan_json}
    if public:
        data["is_public"] = "1"
    r = c.post("/startups", data=data, follow_redirects=False)
    assert r.status_code == 303
    return r.headers["location"]  # e.g. /startups/<id>


# ---------- validation ----------
def test_idea_too_short_is_rejected():
    try:
        IdeaIn(idea="short")
        assert False, "should have failed"
    except Exception:
        pass


def test_mock_plans_match_schema_for_many_ideas():
    for idea in ["finance app for students", "travel planner for hills", "healthy meal delivery",
                 "online tutor course platform", "resume and hiring tool", "something for pets 12345"]:
        GeneratedPlan.model_validate(create_mock_plan(idea))


# ---------- auth ----------
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_protected_pages_redirect_to_login(client):
    for url in ["/dashboard", "/generate"]:
        r = client.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login"


def test_register_login_logout(client):
    mail = signup(client)
    assert client.get("/dashboard").status_code == 200
    client.post("/logout")
    assert client.get("/dashboard", follow_redirects=False).status_code == 303
    r = client.post("/login", data={"email": mail, "password": "password123"}, follow_redirects=False)
    assert r.status_code == 303
    assert client.get("/dashboard").status_code == 200


def test_bad_login_and_duplicate_and_weak_password(client):
    mail = signup(client)
    client.post("/logout")
    r = client.post("/login", data={"email": mail, "password": "wrongpass1"})
    assert r.status_code == 401 and "Incorrect email or password" in r.text
    r = client.post("/register", data={"name": "X", "email": mail, "password": "password123"})
    assert r.status_code == 409
    r = client.post("/register", data={"name": "X", "email": email(), "password": "short"})
    assert r.status_code == 400 and "at least 8" in r.text


# ---------- plans ----------
def test_generate_save_view_delete(client):
    signup(client)
    url = generate_and_save(client)
    r = client.get(url)
    assert r.status_code == 200 and "Disclaimer" in r.text
    assert "Saved" not in r.text  # sanity
    assert url.split("/")[-1] in client.get("/dashboard").text
    sid = url.split("/")[-1]
    r = client.post(f"/startups/{sid}/delete", follow_redirects=False)
    assert r.status_code == 303
    assert client.get(url).status_code == 404


def test_generate_validation_error(client):
    signup(client)
    r = client.post("/generate", data={"idea": "tiny"})
    assert r.status_code == 400 and "10 to 1000" in r.text


def test_save_rejects_tampered_plan(client):
    signup(client)
    r = client.post("/startups", data={"original_idea": IDEA, "plan_json": '{"startupName": "x"}'})
    assert r.status_code == 400


def test_private_plan_hidden_from_others_and_public_visible(client, make_client):
    signup(client)
    url = generate_and_save(client)  # private
    other = make_client()
    assert other.get(url).status_code == 404            # signed out
    signup(other)
    assert other.get(url).status_code == 404            # signed in as someone else
    assert other.post(f"{url}/delete", follow_redirects=False).status_code == 404
    assert other.post(f"{url}/toggle-public", follow_redirects=False).status_code == 404
    # owner publishes -> now visible to others and in /explore
    assert client.post(f"{url}/toggle-public", follow_redirects=False).status_code == 303
    assert other.get(url).status_code == 200
    anon = make_client()
    assert anon.get(url).status_code == 200
    assert url.split("/")[-1] in anon.get("/explore").text
    assert "Delete" not in anon.get(url).text  # no owner buttons for visitors


def test_explore_search(client):
    signup(client)
    generate_and_save(client, public=True)  # FinTech plan
    assert "FinPilot" in client.get("/explore?search=fintech").text
    assert "No published plans found" in client.get("/explore?search=zzzznotfound").text


def test_xss_is_escaped(client):
    signup(client)
    idea = "<script>alert(1)</script> app for students to learn"
    r = client.post("/generate", data={"idea": idea})
    assert "<script>alert(1)</script>" not in r.text
    assert "&lt;script&gt;" in r.text


def test_unknown_page_is_404(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "Page not found" in r.text
