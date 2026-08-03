"""沙箱权限统一配置。

从 agent.yml 的 sandbox 段读取：
- 文件系统只读/可写根路径（区分 Windows / Linux）
- shell 黑名单开关
- 代码执行超时上限
- 桌面 GUI 控制开关 + 截屏目录

所有工具模块统一从此模块取策略，避免散落在各处。

判定规则：
  - 路径同时命中 readonly_root 和 writable_root 时，readonly 优先（拒绝写）
  - 既不在 readonly 也不在 writable 内的路径：默认拒绝写，允许读
    （避免随手写到任意位置；读允许但需在工具内显式校验）
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Tuple

from AIRAGAgent.utils.config_handler import agent_conf
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.paths import PROJECT_ROOT, UPLOAD_DIR

# ── 解析配置 ──
_sb = agent_conf.get("sandbox", {}) if isinstance(agent_conf, dict) else {}

# 判定当前平台
IS_WINDOWS = sys.platform == "win32"
_platform_key = "windows" if IS_WINDOWS else "linux"


def _normalize_root(p: str) -> str:
    """归一化根路径用于前缀匹配。

    支持展开：
    - ~ 和 ${ENV_VAR}
    - ${PROJECT_ROOT}（项目根目录的绝对路径）
    Windows: "C:\\" -> "c:\\"（小写盘符 + 反斜杠）
    Linux:   "/etc" -> "/etc"（保留原样）

    末尾统一带分隔符，便于 startswith 判定。
    """
    if not p:
        return ""
    # 注入 PROJECT_ROOT 环境变量后展开 ~ 和 ${VAR}
    os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
    p = os.path.expandvars(os.path.expanduser(p))
    if IS_WINDOWS:
        # Windows 路径不区分大小写，统一小写
        s = p.replace("/", "\\").lower()
        if not s.endswith("\\"):
            s += "\\"
        return s
    else:
        s = p.rstrip("/")
        return s  # Linux 用 startswith + "/" 判定，不补尾斜杠


# 读取并归一化根路径列表
_raw_readonly = (_sb.get("fs_readonly_roots", {}) or {}).get(_platform_key, [])
_raw_writable = (_sb.get("fs_writable_roots", {}) or {}).get(_platform_key, [])

READONLY_ROOTS: List[str] = [_normalize_root(p) for p in _raw_readonly if p]
WRITABLE_ROOTS: List[str] = [_normalize_root(p) for p in _raw_writable if p]

# 默认工作目录（展开 ${PROJECT_ROOT} 等变量）
_fs_default_root_raw = _sb.get("fs_default_root", "") or ""
if _fs_default_root_raw:
    # 用环境变量展开（PROJECT_ROOT 已在 _normalize_root 调用前注入 os.environ）
    os.environ.setdefault("PROJECT_ROOT", str(PROJECT_ROOT))
    _fs_default_root_raw = os.path.expandvars(os.path.expanduser(_fs_default_root_raw))
    DEFAULT_FS_ROOT = Path(_fs_default_root_raw)
else:
    DEFAULT_FS_ROOT = UPLOAD_DIR

# 确保 workspace 目录存在
DEFAULT_FS_ROOT.mkdir(parents=True, exist_ok=True)

# Shell 开关
SHELL_DANGEROUS_ENABLED: bool = bool(_sb.get("shell_dangerous_enabled", False))

# 代码超时上限
CODE_TIMEOUT_MAX: int = int(_sb.get("code_timeout_max", 60))

# 桌面 GUI
_desktop_cfg_enabled: bool = bool(_sb.get("desktop_enabled", True))
_screenshot_dir_rel: str = _sb.get("desktop_screenshot_dir", "uploads/screenshots") or "uploads/screenshots"
SCREENSHOT_DIR: Path = (PROJECT_ROOT / _screenshot_dir_rel).resolve()
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _is_path_under(path_str: str, root: str) -> bool:
    """判定 path_str 是否在 root 目录下（含 root 自身）。

    Windows：忽略大小写，比较小写化后的字符串前缀
    Linux：大小写敏感，比较 startswith + "/"
    """
    if not root:
        return False
    if IS_WINDOWS:
        # path 必须是绝对路径，归一化为小写 + 反斜杠
        try:
            p = str(Path(path_str).resolve()).replace("/", "\\").lower()
        except Exception:
            p = path_str.replace("/", "\\").lower()
        if not p.endswith("\\"):
            p += "\\"
        # root 末尾已带 \\
        return p.startswith(root)
    else:
        try:
            p = str(Path(path_str).resolve())
        except Exception:
            p = path_str
        # root 不带尾斜杠；判定 p == root 或 p.startswith(root + "/")
        if p == root:
            return True
        return p.startswith(root + "/")


def check_path_permission(path_str: str, mode: str) -> Tuple[bool, str]:
    """检查对 path_str 的操作是否被允许。

    Args:
        path_str: 目标绝对路径
        mode: "r" / "w" / "d"（读/写/删）

    Returns:
        (allowed, reason)
        allowed=True 时 reason 为空字符串
        allowed=False 时 reason 为拒绝原因
    """
    if not path_str:
        return False, "空路径"

    # 读模式：任何路径都允许读（除非是沙盒敏感配置，这里暂不限制）
    if mode == "r":
        return True, ""

    # 写/删模式：writable 优先于 readonly
    # （允许在只读根内挖出可写子目录，如 C:\ 只读但 ~/Desktop 可写）
    try:
        resolved = str(Path(path_str).resolve())
    except Exception as e:
        return False, f"路径解析失败: {e}"

    # 先检查 writable：命中任一即可写（即使同时位于 readonly 内）
    for r in WRITABLE_ROOTS:
        if _is_path_under(resolved, r):
            return True, ""

    # 再检查 readonly：命中 readonly 直接拒绝
    for r in READONLY_ROOTS:
        if _is_path_under(resolved, r):
            return False, f"路径 [{resolved}] 位于只读根 [{r}] 内，禁止写/删操作"

    # 既不在 readonly 也不在 writable：默认拒绝写
    return False, (
        f"路径 [{resolved}] 不在可写根列表内，禁止写/删。"
        f"可写根: {WRITABLE_ROOTS}"
    )


def is_desktop_available() -> bool:
    """判定桌面 GUI 工具是否可用。

    规则：
    1. 配置 desktop_enabled=False → 禁用
    2. Linux 上无 DISPLAY 环境变量 → 禁用
    3. pyautogui / Pillow 未安装 → 禁用
    """
    if not _desktop_cfg_enabled:
        return False

    if not IS_WINDOWS:
        # Linux 需要 DISPLAY
        if not os.environ.get("DISPLAY"):
            return False

    # 检测依赖
    try:
        import pyautogui  # noqa: F401
        from PIL import Image  # noqa: F401
        return True
    except ImportError as e:
        logger.warning(f"[sandbox] 桌面 GUI 工具依赖缺失，自动禁用: {e}")
        return False


# ── 国内镜像配置（加速下载）──
_mirrors = _sb.get("mirrors", {}) or {}
PYPI_MIRROR: str = _mirrors.get("pypi", "") or ""
PLAYWRIGHT_MIRROR: str = _mirrors.get("playwright", "") or ""

# playwright 下载镜像 + 浏览器存放路径：在进程启动时注入环境变量
# 1. PLAYWRIGHT_DOWNLOAD_HOST：让 playwright install 走镜像下载
# 2. PLAYWRIGHT_BROWSERS_PATH：把浏览器装到 workspace/.playwright 下，避免 TRAE 沙箱拦截 AppData 写入
if PLAYWRIGHT_MIRROR:
    os.environ.setdefault("PLAYWRIGHT_DOWNLOAD_HOST", PLAYWRIGHT_MIRROR)
_PLAYWRIGHT_BROWSERS_PATH = str(PROJECT_ROOT / "workspace" / ".playwright")
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", _PLAYWRIGHT_BROWSERS_PATH)


# 启动时打印一次当前策略，便于排查
logger.info(
    f"[sandbox] 平台={_platform_key} | readonly={READONLY_ROOTS} | writable={WRITABLE_ROOTS} "
    f"| shell_dangerous={SHELL_DANGEROUS_ENABLED} | timeout_max={CODE_TIMEOUT_MAX} "
    f"| desktop_available={is_desktop_available()}"
    f"| pypi_mirror={'on' if PYPI_MIRROR else 'off'} | playwright_mirror={'on' if PLAYWRIGHT_MIRROR else 'off'}"
)
