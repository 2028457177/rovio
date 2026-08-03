"""注册 / 登录 / me 鉴权主流程 + 入参校验。"""
import time


def _uniq(prefix="u"):
    return f"{prefix}_{int(time.time() * 1000) % 100000000}"


def test_register_success(client):
    username = _uniq()
    resp = client.post("/api/auth/register", json={
        "username": username, "password": "Test123456", "display_name": "测试用户",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "token" in data and data["token"]
    assert data["user"]["username"] == username
    assert data["user"]["display_name"] == "测试用户"
    assert data["user"]["role"] == "user"
    assert "id" in data["user"]


def test_register_duplicate(client, register_user):
    user, _ = register_user(username=_uniq("dup"))
    resp = client.post("/api/auth/register", json={
        "username": user["username"], "password": "Test123456",
    })
    assert resp.status_code == 409
    assert "已存在" in resp.json()["error"]


def test_register_validation(client):
    # 空用户名
    r = client.post("/api/auth/register", json={"username": "", "password": "Test123456"})
    assert r.status_code == 400
    # 用户名过短
    r = client.post("/api/auth/register", json={"username": "ab", "password": "Test123456"})
    assert r.status_code == 400
    # 用户名过长
    r = client.post("/api/auth/register", json={"username": "x" * 51, "password": "Test123456"})
    assert r.status_code == 400
    # 密码过短
    r = client.post("/api/auth/register", json={"username": _uniq(), "password": "12345"})
    assert r.status_code == 400


def test_login_success(client, register_user):
    user, _ = register_user(username=_uniq("login"), password="Test123456")
    resp = client.post("/api/auth/login", json={
        "username": user["username"], "password": "Test123456",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "token" in data and data["token"]
    assert data["user"]["username"] == user["username"]


def test_login_wrong_password(client, register_user):
    user, _ = register_user(username=_uniq("wp"))
    resp = client.post("/api/auth/login", json={
        "username": user["username"], "password": "WrongPass999",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/auth/login", json={
        "username": "no_such_user_xyz", "password": "whatever",
    })
    assert resp.status_code == 401


def test_login_empty_creds(client):
    resp = client.post("/api/auth/login", json={"username": "", "password": ""})
    assert resp.status_code == 400


def test_me_with_valid_token(client, register_user):
    user, token = register_user(username=_uniq("me"))
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["user"]["username"] == user["username"]
    assert body["user"]["role"] == "user"


def test_me_without_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token(client):
    resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert resp.status_code == 401


def test_token_via_query_param(client, register_user):
    """JWT 也支持 ?token= 查询参数方式（文件下载等场景）。"""
    _, token = register_user(username=_uniq("q"))
    resp = client.get("/api/auth/me", params={"token": token})
    assert resp.status_code == 200
