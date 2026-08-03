"""权限边界：401（无 token）/ 403（非管理员访问管理端）/ 404（访问他人个人库）。"""


# ====== 401：缺少 token ======

def test_admin_list_without_token(client):
    resp = client.get("/api/admin/kb/list")
    assert resp.status_code == 401


def test_user_mine_without_token(client):
    resp = client.get("/api/kb/mine")
    assert resp.status_code == 401


def test_create_personal_kb_without_token(client):
    resp = client.post("/api/kb/mine", json={"name": "x"})
    assert resp.status_code == 401


# ====== 403：普通用户访问管理端 ======

def test_user_cannot_access_admin_list(client, user_headers):
    resp = client.get("/api/admin/kb/list", headers=user_headers)
    assert resp.status_code == 403


def test_user_cannot_create_global_kb(client, user_headers):
    resp = client.post("/api/admin/kb/create", headers=user_headers, json={"name": "x"})
    assert resp.status_code == 403


# ====== 404：访问他人个人库 ======

def test_user_cannot_access_others_personal_kb(client, make_user_token):
    """用户 A 建个人库，用户 B 访问应 404（归属校验，不暴露存在性）。"""
    token_a = make_user_token(2001, "alice")
    token_b = make_user_token(2002, "bob")

    r = client.post("/api/kb/mine", headers={"Authorization": f"Bearer {token_a}"}, json={"name": "alice 私库"})
    kb_id = r.json()["kb"]["id"]

    # B 访问 A 的库 → 404
    resp = client.get(f"/api/kb/mine/{kb_id}/documents", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404

    # B 尝试删除 A 的库 → 404
    resp = client.delete(f"/api/kb/mine/{kb_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


def test_invalid_token_rejected(client):
    resp = client.get("/api/kb/mine", headers={"Authorization": "Bearer not.a.valid.jwt"})
    assert resp.status_code == 401


def test_admin_token_accesses_admin_list(client, admin_headers):
    """管理员 token 能正常访问管理端（正向校验 admin 鉴权链路）。"""
    resp = client.get("/api/admin/kb/list", headers=admin_headers)
    assert resp.status_code == 200
