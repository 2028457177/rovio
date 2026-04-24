"""
总结服务类:用户提问，搜索参考资料，将提问和参考资料提交给模型，让模型总结回复
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from AIRAGAgent.rag.vector_store import VectorStoreService
from AIRAGAgent.utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from AIRAGAgent.model.factory import chat_model
from AIRAGAgent.model.local_factory import local_chat_model
# 打印提示词
def print_prompt(prompt):
    print("="*50)
    print(prompt.to_string())
    print("="*50)
    return prompt
# 总结服务类
class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()    # 向量数据库服务类
        self.retriever = self.vector_store.get_retriever()    # 检索器
        self.prompt_text = load_rag_prompts()    # 加载提示词
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)    # 提示词模板
        self.model = local_chat_model    # 聊天模型
        self.chain = self._init_chain()    # 初始化链
    # 初始化链
    def _init_chain(self):
        chian = self.prompt_template | print_prompt | self.model |StrOutputParser()
        return chian
    # 检索文档
    def retrieve_doce(self,query:str) -> list[Document]:
        return self.retriever.invoke(query)
    # 总结回复
    def rag_summarize(self,query:str) -> str:
        context_docs = self.retrieve_doce(query)
        context = ""
        counter = 0
        # 遍历文档，将文档内容和元数据拼接起来
        for doc in context_docs:
            counter += 1
            context += f"【参考资料{counter}】: 参考资料:{doc.page_content}| 参考元数据:{doc.metadata}\n"
        return self.chain.invoke(
            {
                    "input":query,
                    "context":context,
            }
        )


if __name__ == '__main__':
    rag = RagSummarizeService()

    print(rag.rag_summarize("小户型适合哪些扫地机器人"))