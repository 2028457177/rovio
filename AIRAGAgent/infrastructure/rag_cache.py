import hashlib
import json
from typing import Optional, List
from AIRAGAgent.infrastructure.redis_client import get_redis_client, is_redis_available
from AIRAGAgent.utils.config_handler import redis_conf
from AIRAGAgent.utils.logger_handler import logger

RAG_CACHE_PREFIX = "rag_cache:"
RAG_CACHE_TTL = int(redis_conf.get("rag_cache", {}).get("ttl", 1800))


def _cache_key(query: str) -> str:
    query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
    return f"{RAG_CACHE_PREFIX}{query_hash}"


def get_cached_rag_result(query: str) -> Optional[List[dict]]:
    if not is_redis_available():
        return None
    try:
        client = get_redis_client()
        key = _cache_key(query)
        data = client.get(key)
        if data:
            client.expire(key, RAG_CACHE_TTL)
            results = json.loads(data)
            logger.debug(f"RAG 缓存命中: {query[:30]}...")
            return results
        return None
    except Exception as e:
        logger.warning(f"RAG 缓存读取失败: {e}")
        return None


def cache_rag_result(query: str, results: List[dict]) -> bool:
    if not is_redis_available():
        return False
    try:
        client = get_redis_client()
        key = _cache_key(query)
        data = json.dumps(results, ensure_ascii=False)
        client.setex(key, RAG_CACHE_TTL, data)
        logger.debug(f"RAG 缓存已写入: {query[:30]}... TTL={RAG_CACHE_TTL}s")
        return True
    except Exception as e:
        logger.warning(f"RAG 缓存写入失败: {e}")
        return False


def invalidate_rag_cache() -> bool:
    if not is_redis_available():
        return False
    try:
        client = get_redis_client()
        cursor = 0
        count = 0
        while True:
            cursor, keys = client.scan(cursor, match=f"{RAG_CACHE_PREFIX}*", count=100)
            if keys:
                client.delete(*keys)
                count += len(keys)
            if cursor == 0:
                break
        logger.info(f"已清除 {count} 条 RAG 缓存")
        return True
    except Exception as e:
        logger.warning(f"RAG 缓存清除失败: {e}")
        return False
