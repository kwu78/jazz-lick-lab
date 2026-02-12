import logging

import redis
from rq import Worker, Queue

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    conn = redis.from_url(settings.redis_url)
    queues = [Queue("default", connection=conn)]
    worker = Worker(queues, connection=conn)
    worker.work(with_scheduler=True)
