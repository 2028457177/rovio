import os
import re
from docx import Document
from langchain_core.tools import tool
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.model.local_factory import local_chat_model
from AIRAGAgent.utils.path_tool import get_abs_path


@tool(description="自动填写Word文件标签。根据标签名称由AI生成相应内容。")
def auto_fill_word(template_path: str) -> str:
    """
    Args:
        template_path: 需要填写的 Word 文件路径 
    """
    try:
        # 1. 打开 Word 文档
        doc_abs_path = get_abs_path(template_path)
        doc = Document(doc_abs_path)

        # 2. 遍历文档查找标签
        for paragraph in doc.paragraphs:
            # 匹配形如 {填写活动感受} 的标签
            tags = re.findall(r'\{.*?\}', paragraph.text)
            for tag in tags:
                # 让 AI 根据标签名称生成内容
                prompt = f"请根据标签名称'{tag[1:-1]}'创作一段合适的内容，要求自然且符合语境。"
                ai_content = local_chat_model.invoke(prompt).content
                paragraph.text = paragraph.text.replace(tag, ai_content)

                # 3. 处理表格中的单元格（Word文档可能包含表格）
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        tags = re.findall(r'\{.*?\}', paragraph.text)
                        for tag in tags:
                            prompt = f"请根据标签名称'{tag[1:-1]}'创作一段合适的内容，要求自然且符合语境。"
                            ai_content = local_chat_model.invoke(prompt).content
                            paragraph.text = paragraph.text.replace(tag, ai_content)

        # 4. 保存到桌面
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "已填写的文档.docx")
        doc.save(desktop_path)

        return f"文件处理完成，已保存至桌面：{desktop_path}"
    except Exception as e:
        return f"处理失败：{str(e)}"