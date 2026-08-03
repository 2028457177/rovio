"""用户端个人知识库 CRUD（/api/kb/*）。"""


def test_mine_empty(client, user_headers):
    resp = client.get("/api/kb/mine", headers=user_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kbs"] == []
    assert body["global_kbs"] == []


def test_create_personal_kb(client, user_headers):
    resp = client.post("/api/kb/mine", headers=user_headers, json={
        "name": "我的知识库", "description": "私人",
    })
    assert resp.status_code == 200, resp.text
    kb = resp.json()["kb"]
    assert kb["name"] == "我的知识库"
    assert kb["scope"] == "personal"
    assert kb["owner_user_id"] == 1001  # user_token fixture 的 user_id
    assert "id" in kb


def test_mine_lists_personal_and_global(client, user_headers, admin_headers):
    """用户 mine 列表同时返回个人库 + 已启用的全局库。"""
    # 管理员建一个全局库
    client.post("/api/admin/kb/create", headers=admin_headers, json={"name": "全局"})
    # 用户建一个个人库
    client.post("/api/kb/mine", headers=user_headers, json={"name": "私人"})

    resp = client.get("/api/kb/mine", headers=user_headers)
    body = resp.json()
    assert len(body["kbs"]) == 1
    assert body["kbs"][0]["name"] == "私人"
    assert len(body["global_kbs"]) >= 1
    assert body["global_kbs"][0]["name"] == "全局"


def test_patch_personal_kb(client, user_headers):
    r = client.post("/api/kb/mine", headers=user_headers, json={"name": "原名"})
    kb_id = r.json()["kb"]["id"]

    resp = client.patch(f"/api/kb/mine/{kb_id}", headers=user_headers, json={"name": "新名"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["kb"]["name"] == "新名"


def test_get_personal_documents(client, user_headers):
    r = client.post("/api/kb/mine", headers=user_headers, json={"name": "私人"})
    kb_id = r.json()["kb"]["id"]

    resp = client.get(f"/api/kb/mine/{kb_id}/documents", headers=user_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["documents"] == []


def test_delete_personal_kb(client, user_headers):
    r = client.post("/api/kb/mine", headers=user_headers, json={"name": "待删"})
    kb_id = r.json()["kb"]["id"]

    resp = client.delete(f"/api/kb/mine/{kb_id}", headers=user_headers)
    assert resp.status_code == 200, resp.text

    mine = client.get("/api/kb/mine", headers=user_headers).json()["kbs"]
    assert all(k["id"] != kb_id for k in mine)
