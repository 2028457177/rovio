"""管理端全局知识库 CRUD（/api/admin/kb/*）。"""


def test_list_empty(client, admin_headers):
    resp = client.get("/api/admin/kb/list", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"kbs": []}


def test_create_global_kb(client, admin_headers):
    resp = client.post("/api/admin/kb/create", headers=admin_headers, json={
        "name": "全局知识库A", "biz_line": "demo", "description": "测试用",
    })
    assert resp.status_code == 200, resp.text
    kb = resp.json()["kb"]
    assert kb["name"] == "全局知识库A"
    assert kb["scope"] == "global"
    assert kb["biz_line"] == "demo"
    assert kb["is_enabled"] == 1
    assert "id" in kb


def test_create_then_list(client, admin_headers):
    client.post("/api/admin/kb/create", headers=admin_headers, json={"name": "KB1"})
    client.post("/api/admin/kb/create", headers=admin_headers, json={"name": "KB2"})
    resp = client.get("/api/admin/kb/list", headers=admin_headers)
    assert resp.status_code == 200
    kbs = resp.json()["kbs"]
    assert len(kbs) == 2
    names = {k["name"] for k in kbs}
    assert names == {"KB1", "KB2"}


def test_patch_kb(client, admin_headers):
    r = client.post("/api/admin/kb/create", headers=admin_headers, json={"name": "原名"})
    kb_id = r.json()["kb"]["id"]

    resp = client.patch(f"/api/admin/kb/{kb_id}", headers=admin_headers, json={
        "name": "新名", "is_enabled": False,
    })
    assert resp.status_code == 200, resp.text
    kb = resp.json()["kb"]
    assert kb["name"] == "新名"
    assert kb["is_enabled"] == 0


def test_get_documents_empty(client, admin_headers):
    r = client.post("/api/admin/kb/create", headers=admin_headers, json={"name": "空库"})
    kb_id = r.json()["kb"]["id"]

    resp = client.get(f"/api/admin/kb/{kb_id}/documents", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["documents"] == []
    assert body["kb"]["id"] == kb_id


def test_get_documents_kb_not_found(client, admin_headers):
    resp = client.get("/api/admin/kb/999999/documents", headers=admin_headers)
    assert resp.status_code == 404


def test_delete_kb(client, admin_headers):
    r = client.post("/api/admin/kb/create", headers=admin_headers, json={"name": "待删"})
    kb_id = r.json()["kb"]["id"]

    resp = client.delete(f"/api/admin/kb/{kb_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text

    # 删除后列表里没了
    kbs = client.get("/api/admin/kb/list", headers=admin_headers).json()["kbs"]
    assert all(k["id"] != kb_id for k in kbs)


def test_delete_kb_not_found(client, admin_headers):
    resp = client.delete("/api/admin/kb/999999", headers=admin_headers)
    assert resp.status_code == 404
