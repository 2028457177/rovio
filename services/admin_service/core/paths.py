"""本服务路径（以服务目录为基准，可用环境变量覆盖，支持脱离项目根独立运行）。"""
import os

# core/ 的上一级 = 服务目录
SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.getenv("LOG_DIR", os.path.join(SERVICE_ROOT, "logs"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(SERVICE_ROOT, "data", "uploads"))
WORKSPACE_DIR = os.getenv("WORKSPACE_DIR", os.path.join(SERVICE_ROOT, "data", "workspace"))


def get_abs_path(rel_path: str) -> str:
    """相对服务目录的路径转绝对路径。"""
    if os.path.isabs(rel_path):
        return rel_path
    return os.path.join(SERVICE_ROOT, rel_path)
