"""密码修改 + 安全问题找回密码。"""
import time


def _uniq(prefix="u"):
    return f"{prefix}_{int(time.time() * 1000) % 100000000}"


# ====== 修改密码 ======

def test_change_password_success(client, register_user):
    user, token = register_user(username=_uniq("pw"), password="OldPass123")
    resp = client.put("/api/user/password", headers={"Authorization": f"Bearer {token}"}, json={
        "old_password": "OldPass123", "new_password": "NewPass456",
    })
    assert resp.status_code == 200, resp.text
    # 用新密码登录成功
    r = client.post("/api/auth/login", json={
        "username": user["username"], "password": "NewPass456",
    })
    assert r.status_code == 200
    # 旧密码登录失败
    r = client.post("/api/auth/login", json={
        "username": user["username"], "password": "OldPass123",
    })
    assert r.status_code == 401


def test_change_password_wrong_old(client, register_user):
    _, token = register_user(username=_uniq("wold"))
    resp = client.put("/api/user/password", headers={"Authorization": f"Bearer {token}"}, json={
        "old_password": "WrongOld999", "new_password": "NewPass456",
    })
    assert resp.status_code == 400


def test_change_password_same_as_old(client, register_user):
    _, token = register_user(username=_uniq("same"), password="SamePass123")
    resp = client.put("/api/user/password", headers={"Authorization": f"Bearer {token}"}, json={
        "old_password": "SamePass123", "new_password": "SamePass123",
    })
    assert resp.status_code == 400


def test_change_password_too_short(client, register_user):
    _, token = register_user(username=_uniq("short"))
    resp = client.put("/api/user/password", headers={"Authorization": f"Bearer {token}"}, json={
        "old_password": "Test123456", "new_password": "12345",
    })
    assert resp.status_code == 400


def test_change_password_requires_auth(client):
    resp = client.put("/api/user/password", json={"old_password": "x", "new_password": "y"})
    assert resp.status_code == 401


# ====== 安全问题找回密码 ======

def test_security_question_full_flow(client, register_user):
    user, token = register_user(username=_uniq("sq"))
    # 1. 设置安全问题
    resp = client.put("/api/user/security-question", headers={"Authorization": f"Bearer {token}"}, json={
        "question": "你的第一只宠物叫什么？", "answer": "小花",
    })
    assert resp.status_code == 200, resp.text
    # 2. 获取安全问题（找回密码入口）
    resp = client.get("/api/auth/recover/question", params={"username": user["username"]})
    assert resp.status_code == 200
    assert resp.json()["question"] == "你的第一只宠物叫什么？"
    # 3. 用正确答案重置密码
    resp = client.post("/api/auth/recover/reset", json={
        "username": user["username"], "answer": "小花", "new_password": "Recovered789",
    })
    assert resp.status_code == 200, resp.text
    # 4. 用新密码登录成功
    r = client.post("/api/auth/login", json={
        "username": user["username"], "password": "Recovered789",
    })
    assert r.status_code == 200


def test_recover_reset_wrong_answer(client, register_user):
    user, token = register_user(username=_uniq("wa"))
    client.put("/api/user/security-question", headers={"Authorization": f"Bearer {token}"}, json={
        "question": "你的家乡？", "answer": "北京",
    })
    resp = client.post("/api/auth/recover/reset", json={
        "username": user["username"], "answer": "上海", "new_password": "NewPass456",
    })
    assert resp.status_code == 400


def test_recover_question_nonexistent_user(client):
    resp = client.get("/api/auth/recover/question", params={"username": "ghost_user_xyz"})
    assert resp.status_code == 404


def test_security_question_validation(client, register_user):
    _, token = register_user(username=_uniq("val"))
    # 问题过短
    r = client.put("/api/user/security-question", headers={"Authorization": f"Bearer {token}"}, json={
        "question": "ab", "answer": "ans",
    })
    assert r.status_code == 400
    # 答案为空
    r = client.put("/api/user/security-question", headers={"Authorization": f"Bearer {token}"}, json={
        "question": "合法的问题？", "answer": "",
    })
    assert r.status_code == 400
