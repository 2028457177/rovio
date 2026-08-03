"""登录设备管理。"""
import time


def _uniq(prefix="u"):
    return f"{prefix}_{int(time.time() * 1000) % 100000000}"


def test_register_creates_device(client, register_user):
    """注册即记录一个登录设备。"""
    _, token = register_user(username=_uniq("dev"))
    resp = client.get("/api/user/devices", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    devices = resp.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["is_current"] is True
    assert devices[0]["is_revoked"] is False


def test_devices_requires_auth(client):
    resp = client.get("/api/user/devices")
    assert resp.status_code == 401


def test_revoke_device(client, register_user):
    _, token = register_user(username=_uniq("rev"))
    devices = client.get("/api/user/devices", headers={"Authorization": f"Bearer {token}"}).json()["devices"]
    device_id = devices[0]["id"]

    resp = client.delete(f"/api/user/devices/{device_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text

    devices = client.get("/api/user/devices", headers={"Authorization": f"Bearer {token}"}).json()["devices"]
    target = next(d for d in devices if d["id"] == device_id)
    assert target["is_revoked"] is True  # 已撤销
    # is_current 仅表示"token 匹配当前请求来源"，与 revoked 状态独立；
    # 撤销后用同 token 再查仍 is_current=True（这是设计，真实场景前端应清 token 重登）


def test_revoke_nonexistent_device(client, register_user):
    _, token = register_user(username=_uniq("ne"))
    resp = client.delete("/api/user/devices/999999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_revoke_all_others(client, register_user):
    """多端登录后撤销其他设备。"""
    user, token1 = register_user(username=_uniq("multi"))
    # 再登录一次拿第二个 device_token
    r = client.post("/api/auth/login", json={"username": user["username"], "password": "Test123456"})
    token2 = r.json()["token"]

    # token1 视角：撤销除自己外所有
    resp = client.post("/api/user/devices/revoke-all-others", headers={"Authorization": f"Bearer {token1}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["revoked_count"] >= 1

    # token2 已被撤销：调 /api/auth/me 仍可解析 token（get_current_user 不查 DB），
    # 但 devices 列表中该设备 is_revoked=True
    devices = client.get("/api/user/devices", headers={"Authorization": f"Bearer {token1}"}).json()["devices"]
    revoked = [d for d in devices if d["is_revoked"]]
    assert len(revoked) >= 1
