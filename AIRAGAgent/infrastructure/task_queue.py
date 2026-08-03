import json
import uuid
import time
from enum import Enum
from typing import Optional, Callable
from AIRAGAgent.infrastructure.redis_client import get_redis_client, is_redis_available
from AIRAGAgent.utils.config_handler import redis_conf
from AIRAGAgent.utils.logger_handler import logger

TASK_QUEUE_CONFIG = redis_conf.get("task_queue", {})
QUEUE_NAME = TASK_QUEUE_CONFIG.get("name", "agent_task_queue")
MAX_RETRIES = int(TASK_QUEUE_CONFIG.get("max_retries", 3))
RETRY_DELAY = int(TASK_QUEUE_CONFIG.get("retry_delay", 60))

RESULT_KEY_PREFIX = "task_result:"
RESULT_TTL = 3600


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

    def __str__(self):
        return self.value


class TaskType(str, Enum):
    FILL_WORD = "fill_word"
    PLAN_EXECUTE = "plan_execute"   # DeepAgent 整个 plan 后台执行
    PLAN_STEP = "plan_step"         # DeepAgent 单个 step 后台执行（预留）


def enqueue_task(task_type: TaskType, params: dict, priority: int = 0) -> Optional[str]:
    if not is_redis_available():
        logger.warning("Redis 不可用，无法入队任务")
        return None

    task_id = str(uuid.uuid4())
    task_data = {
        "task_id": task_id,
        "task_type": task_type if isinstance(task_type, str) else task_type.value,
        "params": params,
        "status": TaskStatus.PENDING,
        "retries": 0,
        "max_retries": MAX_RETRIES,
        "created_at": time.time(),
        "priority": priority,
        "error": None,
    }

    try:
        client = get_redis_client()
        task_json = json.dumps(task_data, ensure_ascii=False)

        if priority > 0:
            client.zadd(f"{QUEUE_NAME}:priority", {task_id: priority})
            client.hset(f"{QUEUE_NAME}:tasks", task_id, task_json)
        else:
            client.rpush(QUEUE_NAME, task_json)

        logger.info(f"任务已入队: {task_id}, 类型: {task_type}")
        return task_id
    except Exception as e:
        logger.error(f"任务入队失败: {e}")
        return None


def get_task_status(task_id: str) -> Optional[dict]:
    if not is_redis_available():
        return None
    try:
        client = get_redis_client()
        data = client.get(f"{RESULT_KEY_PREFIX}{task_id}")
        if data:
            return json.loads(data)

        task_json = client.hget(f"{QUEUE_NAME}:tasks", task_id)
        if task_json:
            return json.loads(task_json)
        return None
    except Exception as e:
        logger.warning(f"获取任务状态失败: {e}")
        return None


class TaskWorker:
    def __init__(self):
        self._handlers: dict[str, Callable] = {}

    def register_handler(self, task_type: TaskType, handler: Callable):
        self._handlers[task_type.value if not isinstance(task_type, str) else task_type] = handler
        logger.info(f"任务处理器已注册: {task_type}")

    def _process_task(self, task_data: dict) -> dict:
        task_id = task_data["task_id"]
        task_type = task_data["task_type"]
        handler = self._handlers.get(task_type)

        if not handler:
            task_data["status"] = TaskStatus.FAILED
            task_data["error"] = f"未找到任务处理器: {task_type}"
            return task_data

        try:
            result = handler(task_data["params"])
            task_data["status"] = TaskStatus.COMPLETED
            task_data["result"] = result
        except Exception as e:
            task_data["retries"] += 1
            task_data["error"] = str(e)
            if task_data["retries"] < task_data["max_retries"]:
                task_data["status"] = TaskStatus.RETRYING
                logger.warning(f"任务 {task_id} 失败，将在 {RETRY_DELAY}s 后重试 ({task_data['retries']}/{task_data['max_retries']})")
                later_key = f"{QUEUE_NAME}:retry"
                client = get_redis_client()
                client.zadd(later_key, {task_id: time.time() + RETRY_DELAY})
                client.hset(f"{QUEUE_NAME}:tasks", task_id, json.dumps(task_data, ensure_ascii=False))
            else:
                task_data["status"] = TaskStatus.FAILED
                logger.error(f"任务 {task_id} 最终失败: {e}")

        return task_data

    def process_one(self, timeout: int = 0) -> Optional[dict]:
        if not is_redis_available():
            return None

        client = get_redis_client()

        retry_key = f"{QUEUE_NAME}:retry"
        now = time.time()
        retry_tasks = client.zrangebyscore(retry_key, 0, now, start=0, num=1)
        if retry_tasks:
            task_id = retry_tasks[0]
            client.zrem(retry_key, task_id)
            task_json = client.hget(f"{QUEUE_NAME}:tasks", task_id)
            if task_json:
                task_data = json.loads(task_json)
                result_data = self._process_task(task_data)
                self._save_result(client, result_data)
                return result_data

        priority_key = f"{QUEUE_NAME}:priority"
        priority_tasks = client.zrevrange(priority_key, 0, 0)
        if priority_tasks:
            task_id = priority_tasks[0]
            client.zrem(priority_key, task_id)
            task_json = client.hget(f"{QUEUE_NAME}:tasks", task_id)
            if task_json:
                task_data = json.loads(task_json)
                result_data = self._process_task(task_data)
                self._save_result(client, result_data)
                return result_data

        task_json = client.lpop(QUEUE_NAME)
        if task_json:
            task_data = json.loads(task_json)
            result_data = self._process_task(task_data)
            self._save_result(client, result_data)
            return result_data

        return None

    def _save_result(self, client, task_data: dict):
        task_id = task_data["task_id"]
        client.setex(
            f"{RESULT_KEY_PREFIX}{task_id}",
            RESULT_TTL,
            json.dumps(task_data, ensure_ascii=False),
        )
        client.hdel(f"{QUEUE_NAME}:tasks", task_id)

    def run(self, poll_interval: float = 1.0):
        import signal
        import sys

        logger.info(f"任务 Worker 启动，轮询间隔: {poll_interval}s")

        running = True

        if sys.platform != "win32":
            signal.signal(signal.SIGTERM, lambda s, f: setattr(sys.modules[__name__], 'running', False))
            signal.signal(signal.SIGINT, lambda s, f: setattr(sys.modules[__name__], 'running', False))

        while running:
            try:
                result = self.process_one()
                if result is None:
                    time.sleep(poll_interval)
            except KeyboardInterrupt:
                running = False
            except Exception as e:
                logger.error(f"Worker 运行异常: {e}")
                time.sleep(poll_interval)

        logger.info("任务 Worker 已停止")


_worker = TaskWorker()


def get_task_worker() -> TaskWorker:
    return _worker


def fill_word_handler(params: dict) -> str:
    from AIRAGAgent.agent.tools.file_tools import auto_fill_word
    template_path = params.get("template_path", "")
    return auto_fill_word.invoke({"template_path": template_path})


def plan_execute_handler(params: dict) -> dict:
    """DeepAgent plan 后台执行 handler。

    params:
        query: 用户输入
        chat_history: 会话历史 list[dict]
        user_id: int
        session_id: str
    返回：
        {"plan_id": str, "final_answer": str, "success": bool}
    """
    from AIRAGAgent.agent.orchestrator import get_orchestrator
    query = params.get("query", "")
    chat_history = params.get("chat_history") or []
    user_id = int(params.get("user_id", 0))
    session_id = params.get("session_id", "")

    orch = get_orchestrator()
    final_text = orch.execute(query, chat_history, user_id=user_id, session_id=session_id)
    # plan_id 由 Orchestrator 内部创建并持久化，这里从最近的 plan 取
    plan_id = ""
    try:
        from AIRAGAgent.agent.plan import get_session_plan
        plan = get_session_plan(session_id)
        if plan:
            plan_id = plan.id
    except Exception:
        pass
    return {"plan_id": plan_id, "final_answer": final_text[:65000], "success": bool(final_text)}


def register_default_handlers():
    _worker.register_handler(TaskType.FILL_WORD, fill_word_handler)
    _worker.register_handler(TaskType.PLAN_EXECUTE, plan_execute_handler)
