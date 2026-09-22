"""AI 文生图工具（SubAgent imagegen）。

调用火山方舟（Volcano Ark）OpenAI 兼容的 images/generations 接口，
默认模型 doubao-seedream（即梦）。生成的图片：
1. 立刻从临时 URL 下载保存到当前计划专属目录（与 codexec 同目录策略），
   计划收尾时由 Orchestrator 提升到用户当天工作区；
2. 登记进 plan_images_var 清单，最终回复里以内嵌图片形式直接展示，
   用户不需要去「AI 工作区」翻找。

配置（环境变量，见 deploy/backend/.env 与 docker-compose 的 common-env）：
- IMAGEGEN_API_KEY   必填，火山方舟 API Key（ark- 开头）
- IMAGEGEN_API_BASE  选填，默认 https://ark.cn-beijing.volces.com/api/v3
- IMAGEGEN_MODEL     选填，默认 doubao-seedream-5-0-pro-260628

换任何 OpenAI 兼容的文生图服务（如 DALL·E）只需改这三个变量。
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import requests
from langchain_core.tools import tool

from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.paths import get_daily_workspace
from AIRAGAgent.agent.tools.agent_tools import user_id_var
from AIRAGAgent.agent.tools.artifact_tools import (
    current_plan_id_var,
    register_plan_image,
)

# 默认模型/接口（火山方舟北京区）
_DEFAULT_API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
_DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"

# 生图请求/下载超时（Seedream 高质量档可能要 10-60 秒）
_GENERATE_TIMEOUT = 300
_DOWNLOAD_TIMEOUT = 180

# 文件名里的非法字符（含 Windows 保留字符）
_UNSAFE_FILENAME = re.compile(r'[\\/:*?"<>|\r\n\t]')


def _save_dir() -> Path:
    """图片保存目录：当前计划专属目录（与 codexec cwd 一致），
    无计划上下文时回退到当天工作区的 images/ 子目录。"""
    base = Path(get_daily_workspace(user_id_var.get()))
    plan_id = current_plan_id_var.get() or ""
    if plan_id:
        d = base / "tasks" / plan_id
    else:
        d = base / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ext_from_url(url: str) -> str:
    """从下载 URL 猜扩展名，猜不出给 .png。"""
    m = re.search(r"\.(jpe?g|png|webp)(?:[?#]|$)", url, re.IGNORECASE)
    return ("." + m.group(1).lower()) if m else ".png"


@tool(description="""AI 文生图。根据一段文字描述生成一张图片，自动保存并直接显示在对话回复里（无需用户去工作区找文件）。

适用：插画、海报、logo、头像、表情包、概念图、文章配图等创作类图片。
不适用：数据图表（折线图/柱状图/流程图）——请改用 codexec 跑 matplotlib。""")
def generate_image(prompt: str, size: str = "1024x1024", filename: str = "") -> str:
    """根据文字描述生成一张图片。

    Args:
        prompt: 图片内容描述，越具体越好（主体 + 风格 + 色调 + 构图，如"水彩风格的橙色小猫，坐在草地
                上，阳光明媚，暖色调，居中构图"）
        size: 图片尺寸，"宽x高"（如 1024x1024、1280x720、2048x2048），默认 1024x1024
        filename: 可选的保存文件名（不含扩展名，建议用中文描述图片内容），默认按 prompt 自动生成
    """
    api_key = os.getenv("IMAGEGEN_API_KEY") or os.getenv("ARK_API_KEY") or ""
    if not api_key:
        return ("[生图失败] 未配置 IMAGEGEN_API_KEY。"
                "请在 deploy/backend/.env（或 docker-compose 环境变量）里设置火山方舟 API Key 后重启服务。")
    api_base = (os.getenv("IMAGEGEN_API_BASE") or _DEFAULT_API_BASE).rstrip("/")
    model = os.getenv("IMAGEGEN_MODEL") or _DEFAULT_MODEL

    prompt = (prompt or "").strip()
    if not prompt:
        return "[生图失败] prompt 不能为空，请描述要画的图片内容。"

    endpoint = f"{api_base}/images/generations"
    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "response_format": "url",
        "watermark": False,
    }
    try:
        logger.info(f"[imagegen] 请求生图 model={model} size={size} prompt={prompt[:60]!r}")
        t0 = time.time()
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=_GENERATE_TIMEOUT,
        )
        if resp.status_code != 200:
            snippet = resp.text[:300]
            logger.error(f"[imagegen] 生图接口返回 {resp.status_code}: {snippet}")
            return f"[生图失败] 接口返回 HTTP {resp.status_code}：{snippet}"
        data = resp.json().get("data") or []
        image_url = (data[0] or {}).get("url") if data else ""
        if not image_url:
            return f"[生图失败] 接口未返回图片 URL：{resp.text[:300]}"

        # 临时 URL 有时效（24h），立刻下载落到本地工作区
        img_resp = requests.get(image_url, timeout=_DOWNLOAD_TIMEOUT)
        if img_resp.status_code != 200 or not img_resp.content:
            return f"[生图失败] 图片下载失败 HTTP {img_resp.status_code}"
        content = img_resp.content
    except requests.Timeout:
        return f"[生图失败] 请求超时（>{_GENERATE_TIMEOUT}s），可稍后重试或减小尺寸"
    except Exception as e:
        logger.error(f"[imagegen] 生图异常: {e}", exc_info=True)
        return f"[生图失败] {type(e).__name__}: {e}"

    # 文件名：优先用户给的，否则从 prompt 截取；加时间戳后缀防同计划重名
    stem = _UNSAFE_FILENAME.sub("_", (filename or prompt)[:24]).strip("_") or "AI图片"
    ext = _ext_from_url(image_url)
    save_path = _save_dir() / f"{stem}_{int(time.time() * 1000) % 10_000_000}{ext}"
    try:
        save_path.write_bytes(content)
    except Exception as e:
        return f"[生图失败] 图片保存失败: {e}"

    # 登记进计划图片清单 → Orchestrator 收尾时内嵌进最终回复
    register_plan_image(save_path)
    size_kb = len(content) // 1024
    elapsed = time.time() - t0
    logger.info(f"[imagegen] 生图成功: {save_path.name} ({size_kb} KB, {size}, {elapsed:.1f}s)")
    return (
        f"[生图成功] 已生成并保存：{save_path}（{size}，{size_kb} KB，耗时 {elapsed:.0f} 秒）。\n"
        f"图片会在最终回复里直接展示给用户，不要让用户去工作区找文件。"
    )


IMAGEGEN_TOOLS = [generate_image]
