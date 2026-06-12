"""
Agent 服务层 - 封装 Agent 核心业务逻辑
"""
import sys
import os
import asyncio
import contextvars
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
    def _get_session_messages_with_cache(user_id: int, session_id: str) -> list:
        if not session_id:
            return None
        cached = get_cached_session(user_id, session_id)
        if cached is not None:
            return cached
        messages = get_session_messages(user_id, session_id)
        if messages:
            cache_session_messages(user_id, session_id, messages)
        return messages

    @staticmethod
    def _save_session_messages_with_cache(user_id: int, session_id: str, user_message: str, assistant_message: str):
        save_message(user_id, session_id, "user", user_message)
        save_message(user_id, session_id, "assistant", assistant_message)
        full_messages = get_session_messages(user_id, session_id)
        cache_session_messages(user_id, session_id, full_messages)
    
    async def get_response(
        self, 
        user_id: int,
        message: str, 
        session_id: str = None,
        stream: bool = False
    ) -> Dict[str, Any] | AsyncGenerator:
        """
        获取 Agent 回复
        
        Args:
            user_id: 用户 ID
            message: 用户输入的消息
            session_id: 可选的会话 ID
            stream: 是否使用流式输出
            
        Returns:
            包含回复内容的字典或异步生成器
        """
        try:
            if stream:
                return self._stream_response(user_id, message, session_id)
            else:
                return await self._sync_response(user_id, message, session_id)
                
        except Exception as e:
            logger.error(f"[Agent 服务] 获取回复失败：{str(e)}", exc_info=True)
            raise e
    
    async def _sync_response(self, user_id: int, message: str, session_id: str = None) -> Dict[str, Any]:
        """
        同步方式获取回复
        
        Args:
            user_id: 用户 ID
            message: 用户输入的消息
            session_id: 可选的会话 ID
            
        Returns:
            包含回复内容的字典
        """
        try:
            response_chunks = []
            
            async for chunk in self._stream_response(user_id, message, session_id):
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
        user_id: int,
        message: str,
        session_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        流式方式获取回复

        execute_stream 是同步阻塞的（LangGraph + DeepSeek 同步调用），
        若直接在 async def 里 for 迭代会卡死事件循环，导致 uvicorn 无法
        把已 yield 的 chunk 及时发到网络——所有数据会累积到结束才一次性 flush。
        因此把同步迭代放到线程池里跑，用 asyncio.Queue 跨线程传递 chunk，
        主事件循环异步消费，每个 chunk 到达即可立即推送，SSE 才是真正的流式。

        Args:
            user_id: 用户 ID
            message: 用户输入的消息
            session_id: 可选的会话 ID

        Yields:
            回复内容片段
        """
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()
        SENTINEL = object()
        # 捕获当前 asyncio 任务的上下文（含 user_ip_var/lat/lon/user_id_var）。
        # run_in_executor 的子线程不会自动继承 ContextVar，需用 ctx.run 带过去，
        # 否则 get_user_location 等工具在线程里读到的全是 None。
        ctx = contextvars.copy_context()

        def sync_producer():
            try:
                logger.debug(f"[Agent 服务] 开始流式输出，消息：{message[:30]}...")
                chat_history = self._get_session_messages_with_cache(user_id, session_id)
                full_response_parts = []

                for chunk in self.agent.execute_stream(message, chat_history):
                    if isinstance(chunk, dict):
                        if chunk.get("type") == "output":
                            full_response_parts.append(chunk.get("content", ""))
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                    else:
                        content = chunk.strip()
                        if content:
                            full_response_parts.append(content)
                            loop.call_soon_threadsafe(queue.put_nowait, content)

                if session_id:
                    full_response = "".join(full_response_parts)
                    self._save_session_messages_with_cache(user_id, session_id, message, full_response)
            except Exception as e:
                logger.error(f"[Agent 服务] 流式响应失败：{str(e)}", exc_info=True)
                loop.call_soon_threadsafe(queue.put_nowait, e)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

        # 在线程池中跑同步生产者，不 await，靠 SENTINEL 同步结束
        # 用 ctx.run 包裹，让子线程在捕获的上下文中执行，ContextVar 才能正确传递
        loop.run_in_executor(None, lambda: ctx.run(sync_producer))

        while True:
            item = await queue.get()
            if item is SENTINEL:
                break
            if isinstance(item, Exception):
                raise item
            yield item
    
    async def clear_session(self, user_id: int, session_id: str) -> None:
        """
        清除指定会话的历史记录
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
        """
        try:
            clear_session(user_id, session_id)
            invalidate_session(user_id, session_id)
            logger.info(f"[Agent 服务] 已清除会话 {session_id}")
        except Exception as e:
            logger.error(f"[Agent 服务] 清除会话失败：{str(e)}", exc_info=True)
            raise e
    
    async def get_session_history(self, user_id: int, session_id: str) -> list:
        """
        获取会话历史记录
        
        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            
        Returns:
            会话历史列表
        """
        return self._get_session_messages_with_cache(user_id, session_id)
