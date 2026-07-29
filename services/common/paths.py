"""项目路径工具（微服务版）。"""
import os

# services/common/paths.py → services/common/ → services/ → 项目根
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
CONFIG_DIR = os.path.join(PROJECT_ROOT, "AIRAGAgent", "config")


def get_abs_path(rel_path: str) -> str:
    """相对项目根的路径转绝对路径。"""
    if os.path.isabs(rel_path):
        return rel_path
    return os.path.join(PROJECT_ROOT, rel_path)
