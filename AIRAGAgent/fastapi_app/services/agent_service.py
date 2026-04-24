"""
Agent 服务层 - 封装 Agent 核心业务逻辑
"""
import sys
import os
from typing import Dict, Any, AsyncGenerator

# 将项目根目录添加到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.react_agent import ReactAgent
from utils.logger_handler import logger


class AgentService:
    """Agent 服务类，提供异步接口"""
    
    def __init__(self):
        """初始化 Agent"""
        self.agent = ReactAgent()
        # 会话存储（生产环境应该使用 Redis 等）
        self.sessions: Dict[str, list] = {}
    
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
            # 收集所有流式输出块
            response_chunks = []
            
            async for chunk in self._stream_response(message, session_id):
                response_chunks.append(chunk)
            
            # 拼接完整回复
            full_response = "".join(response_chunks).strip()
            
            return {
                "content": full_response,
                "session_id": session_id,
                "sources": [],  # TODO: 从 Agent 中提取参考来源
                "tool_calls": []  # TODO: 从 Agent 中提取工具调用记录
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
            
            # 执行 Agent 并获取流式输出
            for chunk in self.agent.execute_stream(message):
                # 清理和格式化输出
                content = chunk.strip()
                if content:
                    yield content
                    
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
            if session_id in self.sessions:
                del self.sessions[session_id]
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
        return self.sessions.get(session_id, [])
