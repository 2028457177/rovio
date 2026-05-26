import json
from typing import Optional, List, Dict
from AIRAGAgent.infrastructure.redis_client import get_redis_client, is_redis_available
from AIRAGAgent.utils.config_handler import redis_conf
from AIRAGAgent.utils.logger_handler import logger

SESSION_KEY_PREFIX = "session:"
SESSION_TTL = int(redis_conf.get("session_cache", {}).get("ttl", 3600))


def _session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def cache_session_messages(session_id: str, messages: List[Dict[str, str]]) -> bool:
    if not is_redis_available():
        return False
    try:
        client = get_redis_client()
        key = _session_key(session_id)
        data = json.dumps(messages, ensure_ascii=False)
        client.setex(key, SESSION_TTL, data)
        logger.debug(f"会话缓存已写入: {session_id}, {len(messages)} 条消息, TTL={SESSION_TTL}s")
        return True
    except Exception as e:
        logger.warning(f"会话缓存写入失败: {e}")
        return False


def get_cached_session(session_id: str) -> Optional[List[Dict[str, str]]]:
    if not is_redis_available():
        return None
    try:
        client = get_redis_client()
        key = _session_key(session_id)
        data = client.get(key)
        if data:
            client.expire(key, SESSION_TTL)
            messages = json.loads(data)
            logger.debug(f"会话缓存命中: {session_id}, {len(messages)} 条消息")
            return messages
        return None
    except Exception as e:
        logger.warning(f"会话缓存读取失败: {e}")
        return None


def invalidate_session(session_id: str) -> bool:
    if not is_redis_available():
        return False
    try:
        client = get_redis_client()
        key = _session_key(session_id)
        client.delete(key)
        logger.debug(f"会话缓存已失效: {session_id}")
        return True
    except Exception as e:
        logger.warning(f"会话缓存失效失败: {e}")
        return False


def refresh_session_ttl(session_id: str) -> bool:
    if not is_redis_available():
        return False
    try:
        client = get_redis_client()
        key = _session_key(session_id)
        if client.exists(key):
            client.expire(key, SESSION_TTL)
        return True
    except Exception as e:
        logger.warning(f"会话 TTL 刷新失败: {e}")
        return False
