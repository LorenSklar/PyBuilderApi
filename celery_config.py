import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Celery Configuration
CELERY_CONFIG = {
    'broker_url': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'result_backend': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'worker_prefetch_multiplier': 1,
    'task_acks_late': True,
    'worker_max_tasks_per_child': 100,
    'task_soft_time_limit': 30,
    'task_hard_time_limit': 35,
    'worker_disable_rate_limits': True,
    'task_ignore_result': False,
    'task_store_errors_even_if_ignored': True,
}
