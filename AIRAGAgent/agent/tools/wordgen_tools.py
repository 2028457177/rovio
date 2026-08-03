"""Word 文档生成工具（SubAgent wordgen）。

提供 run_word_code：在独立子进程中执行 Python 代码，并预加载 WordDoc 辅助库，
让 Agent 用高层 API（doc.h1 / doc.p / doc.table / doc.save）生成美观 Word 文档，
排版细节由 wordgen_helper.WordDoc 保证，Agent 只需组织内容。

与 codexec 的区别：
- codexec 是通用代码执行，生成 Word 时 LLM 会写裸 python-docx，排版无保障 → 文档丑
- wordgen 专用：预加载 WordDoc，强制走美观排版模板，中文字体/标题层级/表格样式全部内置

工作目录与 codexec 一致：当前计划专属目录 workspace/{user_id}/YYYYMMDD/tasks/<plan_id>/，
相对路径保存的 .docx 自动落到该目录，前端「AI 工作区」可见可下载。
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.utils.paths import get_daily_workspace
from AIRAGAgent.agent.tools.agent_tools import user_id_var
from AIRAGAgent.agent.tools.artifact_tools import current_plan_id_var
from AIRAGAgent.agent.tools.sandbox_config import CODE_TIMEOUT_MAX
# 复用 codexec 的装包工具：python-docx 缺失时可让 Agent 自动补装
from AIRAGAgent.agent.tools.codexec_tools import install_package, list_packages, _exec_cwd, _truncate

# 项目根目录（lc-course/），用于把 AIRAGAgent 加进子进程 PYTHONPATH
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _build_bootstrap() -> str:
    """生成预加载代码：把项目根加入 sys.path 并导入 WordDoc 到命名空间。

    Agent 写的代码可直接用 WordDoc，无需自己 import。
    """
    return (
        "import sys as _sys\n"
        f"_sys.path.insert(0, {_PROJECT_ROOT.as_posix()!r})\n"
        "try:\n"
        "    from AIRAGAgent.agent.tools.wordgen_helper import WordDoc\n"
        "except ImportError as _e:\n"
        "    print('[wordgen] 导入 WordDoc 失败，可能缺少 python-docx:', _e)\n"
        "    raise\n"
    )


@tool(description="执行 Python 代码生成美观 Word 文档。代码中可直接使用 WordDoc 类（无需 import），它已预加载。WordDoc 提供高层 API：doc=WordDoc(标题,subtitle=,author=)；doc.h1/h2/h3(文本)；doc.p(正文)；doc.bullet(要点)；doc.table(表头列表, 数据二维列表)；doc.image(路径)；doc.page_break()；doc.save(文件名)。排版（中文字体/标题层级/段落行距/表格表头底色）已内置，不要写裸 python-docx。文件用相对路径保存（如 doc.save('调研报告/王者荣耀博主调研.docx')）。")
def run_word_code(code: str, timeout: int = 30) -> str:
    """执行 Python 代码（已预加载 WordDoc 辅助库）生成 Word 文档。

    WordDoc API（直接用，无需 import）：
        doc = WordDoc("文档标题", subtitle="副标题", author="署名")
        doc.h1("一、章节")          # 一级标题
        doc.h2("1.1 小节")          # 二级标题
        doc.h3("要点")              # 三级标题
        doc.p("正文段落……")         # 正文（首行缩进、1.5倍行距）
        doc.bullet("列表项")        # 无序列表
        doc.quote("引用内容")       # 引用块
        doc.table(["列1","列2"], [["a","b"],["c","d"]])  # 数据表格
        doc.image("chart.png", width_cm=14, caption="图1")
        doc.page_break()
        path = doc.save("报告.docx")  # 相对路径保存，返回绝对路径
        print("已保存:", path)

    Args:
        code: Python 源代码（多行），使用 WordDoc API 生成文档
        timeout: 最大执行秒数，默认 30，上限由配置决定
    """
    # 限制超时
    try:
        t = int(timeout)
    except (TypeError, ValueError):
        t = 30
    if t < 1:
        t = 1
    if t > CODE_TIMEOUT_MAX:
        t = CODE_TIMEOUT_MAX

    full_code = _build_bootstrap() + "\n" + code
    cwd = _exec_cwd()

    # 子进程环境：把项目根加入 PYTHONPATH，确保 wordgen_helper 及其依赖 docx 可导入
    env = os.environ.copy()
    existing_pp = env.get("PYTHONPATH", "")
    proj_root_str = str(_PROJECT_ROOT)
    if proj_root_str not in existing_pp.split(os.pathsep):
        env["PYTHONPATH"] = (proj_root_str + os.pathsep + existing_pp).rstrip(os.pathsep) if existing_pp else proj_root_str

    kwargs = {
        "input": full_code,
        "capture_output": True,
        "text": True,
        "errors": "replace",
        "timeout": t,
        "cwd": cwd,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        proc = subprocess.run([sys.executable, "-"], **kwargs)
        out = (proc.stdout or "") + (proc.stderr or "")
        return _truncate(out) if out else "[无输出] 请确认代码里调用了 doc.save() 并 print 保存路径。"
    except subprocess.TimeoutExpired:
        return f"[执行超时] 代码运行超过 {t} 秒已被终止。请简化代码或增大 timeout。"
    except Exception as e:
        return f"[执行失败] {type(e).__name__}: {e}"


WORDGEN_TOOLS = [run_word_code, install_package, list_packages]
