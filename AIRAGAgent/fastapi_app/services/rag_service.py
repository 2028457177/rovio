"""
RAG 服务层 - 封装 RAG 核心业务逻辑
"""
import sys
import os
from typing import List, Dict, Any

# 将 AIRAGAgent 目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from AIRAGAgent.rag.rag_service import RagSummarizeService
from AIRAGAgent.rag.vector_store import VectorStoreService
from AIRAGAgent.utils.logger_handler import logger


class RagService:
    """RAG 服务类，提供知识检索功能"""
    
    def __init__(self):
        """初始化 RAG 服务"""
        self.rag_summarizer = RagSummarizeService()
        self.vector_store = VectorStoreService()
    
    async def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 搜索关键词
            top_k: 返回的文档数量
            
        Returns:
            文档列表，每个文档包含内容和元数据
        """
        try:
            logger.debug(f"[RAG 服务] 开始搜索：{query[:30]}...")
            
            # 使用 retriever 检索文档
            retriever = self.vector_store.get_retriever()
            documents = retriever.invoke(query)
            
            # 转换为字典格式
            result = []
            for doc in documents[:top_k]:
                result.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": None  # LangChain 默认不提供分数，可以后续添加
                })
            
            logger.debug(f"[RAG 服务] 检索到 {len(result)} 个文档")
            
            return result
            
        except Exception as e:
            logger.error(f"[RAG 服务] 搜索失败：{str(e)}", exc_info=True)
            raise e
    
    async def summarize(self, query: str) -> str:
        """
        基于 RAG 总结回复
        
        Args:
            query: 用户问题
            
        Returns:
            总结后的回复
        """
        try:
            logger.debug(f"[RAG 服务] 开始总结：{query[:30]}...")
            
            response = self.rag_summarizer.rag_summarize(query)
            
            logger.debug(f"[RAG 服务] 总结完成")
            
            return response
            
        except Exception as e:
            logger.error(f"[RAG 服务] 总结失败：{str(e)}", exc_info=True)
            raise e
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        获取知识库统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 获取向量库统计
            stats = {
                "collection_name": self.vector_store.vector_store._collection.name,
                "total_documents": self.vector_store.vector_store._collection.count(),
                "persist_directory": self.vector_store.vector_store._persist_directory,
            }
            
            logger.info(f"[RAG 服务] 获取统计信息成功")
            
            return stats
            
        except Exception as e:
            logger.error(f"[RAG 服务] 获取统计信息失败：{str(e)}", exc_info=True)
            raise e
    
    async def reload_knowledge_base(self) -> None:
        """
        重新加载知识库
        
        从数据目录中重新加载所有文档
        """
        try:
            logger.info("[RAG 服务] 开始重新加载知识库")
            
            # 调用 vector_store 的 load_document 方法
            self.vector_store.load_document()
            
            logger.info("[RAG 服务] 知识库重新加载完成")
            
        except Exception as e:
            logger.error(f"[RAG 服务] 重新加载知识库失败：{str(e)}", exc_info=True)
            raise e
