"""
Agent 服务层 - 封装 Agent 核心业务逻辑
"""
import sys
import os
from typing import Dict, Any, AsyncGenerator

# 将 AIRAGAgent 目录添加到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from AIRAGAgent.agent.supervisor_agent import SupervisorAgent
from AIRAGAgent.utils.logger_handler import logger
from AIRAGAgent.database import save_message, get_session_messages, clear_session
from AIRAGAgent.infrastructure.session_cache import (
    cache_session_messages,
    get_cached_session,
    invalidate_session,
)


class AgentService:
    """Agent 服务类，提供异步接口"""
    
    def __init__(self):
        """初始化 Agent"""
        self.agent = SupervisorAgent()

    @staticmethod
    def _get_session_messages_with_cache(session_id: str) -> list:
        if not session_id:
            return None
        cached = get_cached_session(session_id)
        if cached is not None:
            return cached
        messages = get_session_messages(session_id)
        if messages:
            cache_session_messages(session_id, messages)
        return messages

    @staticmethod
    def _save_session_messages_with_cache(session_id: str, user_message: str, assistant_message: str):
        save_message(session_id, "user", user_message)
        save_message(session_id, "assistant", assistant_message)
        full_messages = get_session_messages(session_id)
        cache_session_messages(session_id, full_messages)
    
    async def get_response(
        self, 
        message: str, 
        session_id: str = None,
        stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator:
        """
        获取 Agent 回复
        
        Args:
            message: 用户输入的消息
            session_id: 可选的会话 ID
            stream: 是否使用流式输出
            
        Returns:
            包含回复内容的字典或异步生成器
        """
        try:
            if stream:
                return self._stream_response(message, session_id)
            else:
                return await self._sync_response(message, session_id)
                
        except Exception as e:
            logger.error(f"[Agent 服务] 获取回复失败：{str(e)}", exc_info=True)
            raise e
    
    async def _sync_response(self, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        同步方式获取回复
        
        Args:
            message: 用户输入的消息
            session_id: 可选的会话 ID
            
        Returns:
            包含回复内容的字典
        """
        try:
            response_chunks = []
            
            async for chunk in self._stream_response(message, session_id):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "output":
                        response_chunks.append(chunk.get("content", ""))
                else:
                    response_chunks.append(str(chunk))
            
            full_response = "".join(response_chunks).strip()
            
            return {
                "content": full_response,
                "session_id": session_id,
                "sources": [],
                "tool_calls": []
            }
            
        except Exception as e:
            logger.error(f"[Agent 服务] 同步响应失败：{str(e)}", exc_info=True)
            raise e
    
    async def _stream_response(
        self, 
        message: str, 
        session_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        流式方式获取回复
        
        Args:
            message: 用户输入的消息
            session_id: 可选的会话 ID
            
        Yields:
            回复内容片段
        """
        try:
            logger.debug(f"[Agent 服务] 开始流式输出，消息：{message[:30]}...")
            
            chat_history = self._get_session_messages_with_cache(session_id)
            full_response_parts = []
            
            for chunk in self.agent.execute_stream(message, chat_history):
                if isinstance(chunk, dict):
                    if chunk.get("type") == "output":
                        full_response_parts.append(chunk.get("content", ""))
                    yield chunk
                else:
                    content = chunk.strip()
                    if content:
                        full_response_parts.append(content)
                        yield content
            
            if session_id:
                full_response = "".join(full_response_parts)
                self._save_session_messages_with_cache(session_id, message, full_response)
                    
        except Exception as e:
            logger.error(f"[Agent 服务] 流式响应失败：{str(e)}", exc_info=True)
            raise e
    
    async def clear_session(self, session_id: str) -> None:
        """
        清除指定会话的历史记录
        
        Args:
            session_id: 会话 ID
        """
        try:
            clear_session(session_id)
            invalidate_session(session_id)
            logger.info(f"[Agent 服务] 已清除会话 {session_id}")
        except Exception as e:
            logger.error(f"[Agent 服务] 清除会话失败：{str(e)}", exc_info=True)
            raise e
    
    async def get_session_history(self, session_id: str) -> list:
        """
        获取会话历史记录
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话历史列表
        """
        return self._get_session_messages_with_cache(session_id)
