import os
import re
import uuid
from pathlib import Path
from docx import Document
from langchain_core.tools import tool
from AIRAGAgent.model.factory import chat_model

# 上传/下载目录
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@tool(description="自动填写Word文件标签。根据标签名称由AI生成相应内容，填写后的文件可通过返回的下载链接下载。")
def auto_fill_word(template_path: str) -> str:
    """
    接收服务器上已上传的 Word 文件路径，自动查找 {占位标签} 并用 AI 内容填充，
    将填写完成的文件保存到服务器 uploads 目录，返回下载链接。

    Args:
        template_path: 上传到服务器的 Word 文件的绝对路径
    """
    try:
        # 1. 打开 Word 文档
        doc = Document(template_path)

        # 2. 遍历文档查找标签
        all_tags = set()
        for paragraph in doc.paragraphs:
            tags = re.findall(r'\{.*?\}', paragraph.text)
            for tag in tags:
                all_tags.add(tag)
                prompt = f"请根据标签名称'{tag[1:-1]}'创作一段合适的内容，要求自然且符合语境。"
                ai_content = chat_model.invoke(prompt).content
                paragraph.text = paragraph.text.replace(tag, ai_content)

        # 3. 处理表格中的单元格
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        tags = re.findall(r'\{.*?\}', paragraph.text)
                        for tag in tags:
                            all_tags.add(tag)
                            prompt = f"请根据标签名称'{tag[1:-1]}'创作一段合适的内容，要求自然且符合语境。"
                            ai_content = chat_model.invoke(prompt).content
                            paragraph.text = paragraph.text.replace(tag, ai_content)

        # 4. 保存到 uploads 目录
        output_filename = f"filled_{uuid.uuid4().hex[:8]}.docx"
        output_path = UPLOAD_DIR / output_filename
        doc.save(str(output_path))

        if not all_tags:
            return "文档中没有找到需要填写的占位标签（格式为{标签名称}），无需处理。"

        download_url = f"/api/download/{output_filename}"
        tag_count = len(all_tags)
        return (
            f"文件处理完成！共填写了 {tag_count} 个标签。\n\n"
            f"[点击下载已填写的文档]({download_url})"
        )
    except Exception as e:
        return f"处理失败：{str(e)}"