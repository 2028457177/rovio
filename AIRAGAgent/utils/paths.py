"""项目级共享路径常量。

抽出此模块是为了避免 agent_tools 反向依赖 fastapi_app.main 造成循环 import：
main.py 和 agent_tools.py 都需要 UPLOAD_DIR，但 agent_tools 不应依赖 FastAPI 入口。
"""
import shutil
from datetime import date, timedelta
from pathlib import Path

# 项目根目录 = AIRAGAgent/utils/paths.py 的 parent.parent.parent
# 即 lc-course/ 项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 文件上传目录（服务器上存储上传的 Word 文件、头像、课表、生成的文档等）
UPLOAD_DIR = PROJECT_ROOT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# AI 工作区：所有 AI 生成的文件统一收纳到此目录（沙箱可写根）
# 按用户隔离 + 日期分级：workspace/{user_id}/{YYYYMMDD}/（如 workspace/2/20260801/）
# 每个日期子目录独立保留 30 天，超期自动清理。
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# 日期子目录保留天数
DAILY_WORKSPACE_RETAIN_DAYS = 30


def _user_dir(user_id) -> Path:
    """用户工作目录 workspace/{user_id}（user_id 为空时归到 0）。"""
    uid = str(user_id or 0)
    d = WORKSPACE_DIR / uid
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_user_workspace(user_id) -> Path:
    """获取指定用户的 AI 工作区根目录 workspace/{user_id}（自动创建）。"""
    return _user_dir(user_id)


def get_daily_workspace(user_id, day: date | None = None) -> Path:
    """获取指定用户、指定日期（默认今天）的工作子目录，自动创建。

    目录结构：workspace/{user_id}/{YYYYMMDD}/（如 workspace/2/20260801/）。
    run_python_code / run_shell_command 的 cwd 会设为此目录，
    让 AI 代码里用相对路径写文件时自然落到用户当天的子目录。
    """
    if day is None:
        day = date.today()
    daily = _user_dir(user_id) / day.strftime("%Y%m%d")
    daily.mkdir(parents=True, exist_ok=True)
    return daily


def get_screenshot_dir(user_id, day: date | None = None) -> Path:
    """截图专用目录 workspace/{user_id}/{YYYYMMDD}/screenshots/。"""
    d = get_daily_workspace(user_id, day) / "screenshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def cleanup_old_daily_workspaces(max_days: int = DAILY_WORKSPACE_RETAIN_DAYS) -> int:
    """清理超过 max_days 天的日期子目录，返回清理的目录数。

    扫描 workspace/{user_id}/ 下每个用户目录中形如 YYYYMMDD 的 8 位纯数字目录，
    早于 max_days 天前的删除。非日期命名的目录（如 screenshots）不受影响。
    """
    today = date.today()
    cutoff = today - timedelta(days=max_days)
    removed = 0
    try:
        for user_dir in WORKSPACE_DIR.iterdir():
            if not user_dir.is_dir() or user_dir.name.startswith((".", "_")):
                continue
            for entry in user_dir.iterdir():
                if not entry.is_dir():
                    continue
                name = entry.name
                # 仅处理 8 位纯数字命名的目录（YYYYMMDD）
                if len(name) != 8 or not name.isdigit():
                    continue
                try:
                    d = date(int(name[:4]), int(name[4:6]), int(name[6:8]))
                except ValueError:
                    continue
                if d < cutoff:
                    shutil.rmtree(entry, ignore_errors=True)
                    removed += 1
    except Exception:
        pass
    return removed

