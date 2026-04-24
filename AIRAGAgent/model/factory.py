from abc import ABC, abstractmethod
from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from AIRAGAgent.utils.config_handler import rag_conf


# 模型工厂类
class BaseModelFactory(ABC):
    @abstractmethod  #抽象方法
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass

# 聊天模型工厂类
class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return ChatTongyi(model=rag_conf["chat_model_name"],api_key=rag_conf["api_key"])

# 嵌入模型工厂类
class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return DashScopeEmbeddings(model=rag_conf["embedding_model_name"], dashscope_api_key=rag_conf["api_key"])


chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()


