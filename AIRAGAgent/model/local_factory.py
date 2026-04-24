from abc import ABC, abstractmethod
from typing import Optional
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from AIRAGAgent.utils.config_handler import rag_conf


class BaseModelFactory(ABC):
    @abstractmethod  # 抽象方法
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        # 从配置中获取本地模型配置
        return ChatOllama(
            model=rag_conf["local_chat_model_name"],  # 如 "qwen2.5", "llama3.2" 等
            temperature=rag_conf.get("temperature", 0.7),
            base_url=rag_conf.get("ollama_base_url", "http://localhost:11434"),
            num_predict=rag_conf.get("max_tokens", 2048),
            top_k=rag_conf.get("top_k", 40),
            top_p=rag_conf.get("top_p", 0.9),
            repeat_penalty=rag_conf.get("repeat_penalty", 1.1),
            # 可以根据需要添加更多参数
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return OllamaEmbeddings(
            model=rag_conf["local_embedding_model_name"],  # 如 "nomic-embed-text", "bge-m3" 等
            base_url=rag_conf.get("ollama_base_url", "http://localhost:11434"),
        )



# 使用示例 - 默认使用Ollama
local_chat_model = ChatModelFactory().generator()
local_embed_model = EmbeddingsFactory().generator()
