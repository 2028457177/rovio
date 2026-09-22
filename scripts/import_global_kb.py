# -*- coding: utf-8 -*-
"""全局知识库批量导入脚本。

通过 kb_service 管理端 API 把本地目录中的文件上传到指定全局知识库，
并轮询索引状态直到全部 ready/failed。

用法：
    python scripts/import_global_kb.py \
        --dir deploy/kb_global_upload/converted \
        --kb-name 房屋建筑学课程知识库 \
        [--base-url http://81.70.100.57] \
        [--extra-dir deploy/kb_global_upload --ext .xlsx]

鉴权：用 JWT_SECRET_KEY（环境变量，默认与服务端一致的开发默认值）自签管理员令牌；
生产环境若改过密钥，请先 export JWT_SECRET_KEY=...。
注意：服务端 nginx 默认 client_max_body_size=1m，kb_service 单文件上限 20MB，
超限文件请先拆分/转换为文本后再导入。
"""
import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import jwt
import requests

DEFAULT_SECRET = "lc-course-secret-key-2025"


def make_token(secret: str) -> str:
    payload = {
        "user_id": 1,
        "username": "admin",
        "role": "admin",
        "device_token": "kb-import-script",
        "exp": datetime.utcnow() + timedelta(hours=2),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def find_or_create_kb(base: str, headers: dict, name: str, biz_line: str) -> int:
    r = requests.get(f"{base}/api/admin/kb/list", headers=headers, timeout=15)
    r.raise_for_status()
    for kb in r.json().get("kbs", []):
        if kb["name"] == name:
            print(f"[知识库] 已存在：{name} (id={kb['id']})")
            return kb["id"]
    r = requests.post(
        f"{base}/api/admin/kb/create",
        headers=headers,
        json={"name": name, "biz_line": biz_line, "description": ""},
        timeout=15,
    )
    r.raise_for_status()
    kb_id = r.json()["kb"]["id"]
    print(f"[知识库] 已创建：{name} (id={kb_id})")
    return kb_id


def upload_file(base: str, headers: dict, kb_id: int, path: Path) -> dict:
    with open(path, "rb") as f:
        r = requests.post(
            f"{base}/api/admin/kb/{kb_id}/documents",
            headers=headers,
            files=[("files", (path.name, f))],
            timeout=300,
        )
    if r.status_code != 200:
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    return r.json()["results"][0]


def poll_status(base: str, headers: dict, kb_id: int, interval: int = 10) -> list:
    """轮询直到没有 pending/processing 文档，返回最终文档列表。"""
    while True:
        r = requests.get(f"{base}/api/admin/kb/{kb_id}/documents", headers=headers, timeout=15)
        r.raise_for_status()
        docs = r.json().get("documents", [])
        active = [d for d in docs if d["status"] in ("pending", "processing")]
        if not active:
            return docs
        print(f"[索引中] 剩余 {len(active)} 篇：{', '.join(d['filename'] for d in active[:5])}...")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description="全局知识库批量导入")
    ap.add_argument("--dir", required=True, help="待上传文件目录（不递归）")
    ap.add_argument("--kb-name", required=True, help="目标全局知识库名称（不存在则创建）")
    ap.add_argument("--biz-line", default="")
    ap.add_argument("--base-url", default=os.getenv("KB_BASE_URL", "http://localhost:8004"))
    ap.add_argument("--ext", default="", help="只上传这些后缀（逗号分隔，如 .txt,.xlsx），空为全部")
    ap.add_argument("--no-wait", action="store_true", help="上传完不等待索引完成")
    args = ap.parse_args()

    secret = os.getenv("JWT_SECRET_KEY", DEFAULT_SECRET)
    if secret == DEFAULT_SECRET:
        print("[警告] 使用默认 JWT_SECRET_KEY，生产环境如已修改请通过环境变量传入")
    headers = {"Authorization": f"Bearer {make_token(secret)}"}
    base = args.base_url.rstrip("/")

    exts = {e.strip().lower() for e in args.ext.split(",") if e.strip()} if args.ext else None
    files = sorted(
        p for p in Path(args.dir).iterdir()
        if p.is_file() and (exts is None or p.suffix.lower() in exts)
    )
    if not files:
        sys.exit(f"目录 {args.dir} 下没有可上传文件")

    kb_id = find_or_create_kb(base, headers, args.kb_name, args.biz_line)
    print(f"[上传] {len(files)} 个文件 → kb_id={kb_id} ({base})")

    failed = []
    for p in files:
        size_kb = p.stat().st_size // 1024
        res = upload_file(base, headers, kb_id, p)
        if res.get("ok"):
            print(f"  [OK] {p.name} ({size_kb}KB)")
        else:
            failed.append(p.name)
            print(f"  [失败] {p.name}: {res.get('error')}")

    if args.no_wait:
        return
    docs = poll_status(base, headers, kb_id)
    print("\n[最终状态]")
    bad = 0
    for d in docs:
        mark = "" if d["status"] == "ready" else "  <<< 异常"
        if d["status"] != "ready":
            bad += 1
        print(f"  {d['filename']}: {d['status']} ({d['chunk_count']} 块){mark} {d.get('error_msg', '')}")
    if failed or bad:
        sys.exit(f"上传失败 {len(failed)} 个，索引异常 {bad} 个")
    print("[完成] 全部文档索引成功")


if __name__ == "__main__":
    main()
