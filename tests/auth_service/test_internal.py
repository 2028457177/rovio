"""内部接口（供 user_service / admin_service 跨服务调用）。"""
import time


def _uniq(prefix="u"):
    return f"{prefix}_{int(time.time() * 1000) % 100000000}"


def test_internal_get_user(client, register_user):
    user, _ = register_user(username=_uniq("int"))
    resp = client.get(f"/internal/auth/user/{user['id']}")
    assert resp.status_code == 200, resp.text
    body = resp.json()["user"]
    assert body["username"] == user["username"]
    assert "has_security_question" in body


def test_internal_get_user_not_found(client):
    resp = client.get("/internal/auth/user/999999")
    assert resp.status_code == 404


def test_internal_list_users(client, register_user):
    register_user(username=_uniq("list1"))
    register_user(username=_uniq("list2"))
    resp = client.get("/internal/auth/users")
    assert resp.status_code == 200
    users = resp.json()["users"]
    assert len(users) >= 2


def test_internal_get_role(client, register_user):
    user, _ = register_user(username=_uniq("role"))
    resp = client.get(f"/internal/auth/users/{user['id']}/role")
    assert resp.status_code == 200
    assert resp.json()["role"] == "user"


def test_internal_get_role_not_found(client):
    resp = client.get("/internal/auth/users/999999/role")
    assert resp.status_code == 404


def test_internal_reset_password(client, register_user):
    """管理员重置用户密码为默认值 123456789。"""
    user, _ = register_user(username=_uniq("rst"))
    # 路由签名 internal_reset_password(user_id, req: ResetPasswordRequest) —— body 必传，
    # 但 password 有默认值，传空 body 即用默认 123456789
    resp = client.post(f"/internal/auth/users/{user['id']}/reset-password", json={})
    assert resp.status_code == 200, resp.text
    # 用默认密码登录
    r = client.post("/api/auth/login", json={
        "username": user["username"], "password": "123456789",
    })
    assert r.status_code == 200


def test_internal_reset_password_custom(client, register_user):
    user, _ = register_user(username=_uniq("rstc"))
    resp = client.post(f"/internal/auth/users/{user['id']}/reset-password",
                        json={"password": "CustomReset1"})
    assert resp.status_code == 200
    r = client.post("/api/auth/login", json={
        "username": user["username"], "password": "CustomReset1",
    })
    assert r.status_code == 200


def test_internal_reset_password_too_short(client, register_user):
    user, _ = register_user(username=_uniq("rts"))
    resp = client.post(f"/internal/auth/users/{user['id']}/reset-password", json={"password": "12345"})
    assert resp.status_code == 400


def test_internal_delete_user(client, register_user):
    user, token = register_user(username=_uniq("del"))
    resp = client.post(f"/internal/auth/users/{user['id']}/delete")
    assert resp.status_code == 200, resp.text
    # 删除后查不到
    r = client.get(f"/internal/auth/user/{user['id']}")
    assert r.status_code == 404


def test_internal_delete_nonexistent(client):
    resp = client.post("/internal/auth/users/999999/delete")
    assert resp.status_code == 400


def test_internal_cannot_delete_admin(client, models):
    """管理员账号不可被删除。"""
    admin = models.create_user(_uniq("admin"), "AdminPass1", role="admin")
    assert admin is not None
    resp = client.post(f"/internal/auth/users/{admin['id']}/delete")
    assert resp.status_code == 400


def test_internal_cannot_reset_admin_password(client, models):
    admin = models.create_user(_uniq("admin2"), "AdminPass1", role="admin")
    assert admin is not None
    resp = client.post(f"/internal/auth/users/{admin['id']}/reset-password", json={"password": "NewPass456"})
    assert resp.status_code == 400
