import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AIRAGAgent.infrastructure.task_queue import register_default_handlers, get_task_worker

register_default_handlers()
worker = get_task_worker()
worker.run(poll_interval=1.0)
